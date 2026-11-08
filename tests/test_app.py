import io
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import app
from openai import AuthenticationError, NotFoundError


class BackendRouteTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True)
        self.client = app.app.test_client()

    def test_homepage_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_generate_rejects_missing_content(self):
        response = self.client.post("/generate", data={"action": "both"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Veuillez saisir", response.data)

    def test_generate_rejects_invalid_action(self):
        response = self.client.post(
            "/generate",
            data={"text_input": "Cours", "action": "invalid"},
        )
        self.assertEqual(response.status_code, 400)

    def test_generate_rejects_unsupported_upload(self):
        response = self.client.post(
            "/generate",
            data={
                "file_input": (io.BytesIO(b"no"), "notes.exe"),
                "action": "both",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 415)

    @patch.object(app, "generate_ai_content")
    def test_generate_reports_missing_api_configuration(self, generate_content):
        generate_content.side_effect = app.RequestError("GROQ_API_KEY missing", 503)
        response = self.client.post(
            "/generate",
            data={"text_input": "Cours", "action": "resume"},
        )
        self.assertEqual(response.status_code, 503)
        generate_content.assert_called_once()

    @patch.object(app, "get_db_connection")
    @patch.object(app, "generate_ai_content")
    def test_generate_saves_results_and_question_count(self, generate_content, get_connection):
        generate_content.return_value = {
            "resume": "<p>Résumé</p>",
            "quiz": [{
                "question": "Question ?",
                "options": ["Oui", "Non"],
                "reponse_correcte": "Oui",
                "explication": "",
            }],
        }
        cursor = MagicMock()
        cursor.lastrowid = 17
        connection = MagicMock()
        connection.cursor.return_value = cursor
        get_connection.return_value = connection

        response = self.client.post(
            "/generate",
            data={"text_input": "Cours de test", "difficulty": "Facile", "action": "both"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Question ?", response.data)
        self.assertIn(b"quiz_id: 17", response.data)
        self.assertEqual(cursor.execute.call_args.args[1], ("Cours de test", "Facile", "<p>Résumé</p>", 1))
        connection.commit.assert_called_once()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    @patch.object(app, "generate_ai_content")
    def test_sqlite_generation_and_score_save_work_end_to_end(self, generate_content):
        generate_content.return_value = {
            "resume": "<p>Résumé conservé</p>",
            "quiz": [{
                "question": "Question intégrée ?",
                "options": ["Oui", "Non"],
                "reponse_correcte": "Oui",
                "explication": "",
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "test.sqlite3")
            with patch.object(app, "DB_TYPE", "sqlite"), patch.object(
                app, "SQLITE_DB_PATH", database_path
            ):
                response = self.client.post(
                    "/generate",
                    data={"text_input": "Cours de test", "difficulty": "Facile", "action": "both"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Question int", response.data)

                score_response = self.client.post(
                    "/save_score",
                    json={"quiz_id": 1, "score": 1, "total_questions": 1},
                )
                self.assertEqual(score_response.status_code, 200)

                connection = app.get_db_connection()
                try:
                    row = connection.execute(
                        "SELECT topic, score, total_questions FROM quiz_history WHERE id = ?",
                        (1,),
                    ).fetchone()
                finally:
                    connection.close()
                self.assertEqual(row, ("Cours de test", 1, 1))

    def test_score_requires_valid_json_and_values(self):
        response = self.client.post("/save_score", data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/save_score",
            data=json.dumps({"quiz_id": 1, "score": 4, "total_questions": 3}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch.object(app, "get_db_connection")
    def test_score_persists_result(self, get_connection):
        cursor = MagicMock()
        cursor.rowcount = 1
        connection = MagicMock()
        connection.cursor.return_value = cursor
        get_connection.return_value = connection

        response = self.client.post(
            "/save_score",
            json={"quiz_id": 5, "score": 2, "total_questions": 3},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "success"})
        self.assertEqual(cursor.execute.call_args.args[1], (2, 3, 5))
        connection.commit.assert_called_once()

    def test_ai_response_is_validated_and_summary_sanitized(self):
        data = app._validate_ai_content({
            "resume": '<p>Résumé</p><script>alert(1)</script>',
            "quiz": [{
                "question": "Question ?",
                "options": ["Oui", "Non"],
                "reponse_correcte": "Oui",
            }],
        }, "both")
        self.assertNotIn("<script>", data["resume"])
        self.assertEqual(data["quiz"][0]["reponse_correcte"], "Oui")

    def test_ai_response_with_missing_correct_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            app._validate_ai_content({
                "resume": "<p>Résumé</p>",
                "quiz": [{
                    "question": "Question ?",
                    "options": ["Oui", "Non"],
                    "reponse_correcte": "Peut-être",
                }],
            }, "both")

    @patch.dict("os.environ", {}, clear=True)
    def test_ai_generation_fails_clearly_without_api_key(self):
        with self.assertRaises(app.RequestError) as error:
            app.generate_ai_content("Cours", "Moyen")
        self.assertEqual(error.exception.status_code, 503)

    @patch.object(app, "OpenAI")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "retired-model"})
    def test_ai_generation_falls_back_when_configured_model_is_retired(self, openai_client):
        completion = MagicMock()
        completion.choices[0].message.content = json.dumps({
            "resume": "<p>Résumé</p>",
            "quiz": [],
        })
        not_found = NotFoundError(
            "model not found",
            response=MagicMock(
                status_code=404,
                request=MagicMock(),
                headers={},
            ),
            body={"error": "model not found"},
        )
        client = MagicMock()
        client.chat.completions.create.side_effect = [not_found, completion]
        openai_client.return_value = client

        result = app.generate_ai_content("Cours", "Moyen", "resume")

        self.assertEqual(result["resume"], "<p>Résumé</p>")
        self.assertEqual(
            [call.kwargs["model"] for call in client.chat.completions.create.call_args_list],
            ["retired-model", app.DEFAULT_GROQ_MODEL],
        )

    @patch.object(app, "generate_ai_content")
    def test_generate_explains_invalid_groq_key(self, generate_content):
        generate_content.side_effect = AuthenticationError(
            "invalid api key",
            response=MagicMock(
                status_code=401,
                request=MagicMock(),
                headers={},
            ),
            body={"error": "invalid api key"},
        )
        response = self.client.post(
            "/generate",
            data={"text_input": "Cours", "action": "resume"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Groq a refus", response.data)

    def test_quiz_only_response_does_not_require_a_summary(self):
        data = app._validate_ai_content({
            "resume": "",
            "quiz": [{
                "question": "Question ?",
                "options": ["Oui", "Non"],
                "reponse_correcte": "Oui",
            }],
        }, "quiz")
        self.assertEqual(data["resume"], "")
        self.assertEqual(len(data["quiz"]), 1)


if __name__ == "__main__":
    unittest.main()
