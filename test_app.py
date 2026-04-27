import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import asyncio

# Add current directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import ElectionAssistant, sanitize_input, predict

class TestVoteSmart(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "test_key"
        self.assistant = ElectionAssistant()

    def test_assistant_initialization(self):
        """Testing: Test if the assistant initializes correctly with an API key."""
        self.assertIsNotNone(self.assistant)

    def test_sanitize_input(self):
        """Security: Verify input sanitization limits and strips tags."""
        self.assertEqual(sanitize_input("Hello <script>alert('XSS')</script>"), "Hello scriptalert(XSS)/script")
        self.assertEqual(sanitize_input("Normal query?"), "Normal query?")
        self.assertEqual(sanitize_input(""), "")
        self.assertEqual(sanitize_input(None), "")
        self.assertEqual(len(sanitize_input("A" * 3000)), 2000)

    @patch('app.firestore')
    @patch('app.db')
    @patch('app.genai.Client')
    def test_get_response_mock_and_logging(self, mock_genai, mock_db, mock_firestore):
        """Testing: Test get_response_sync and Firestore logging."""
        # Note: mocks are passed bottom-up. mock_genai=Client, mock_db=db, mock_firestore=firestore.
        
        mock_client_instance = MagicMock()
        mock_genai.return_value = mock_client_instance
        
        mock_chat = MagicMock()
        mock_client_instance.chats.create.return_value = mock_chat
        
        mock_response = MagicMock()
        mock_response.text = "This is a test response."
        mock_chat.send_message.return_value = mock_response

        # Ensure mock_db is not None so the if check passes
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_document = MagicMock()
        mock_collection.document.return_value = mock_document
        
        # Mock firestore.SERVER_TIMESTAMP
        mock_firestore.SERVER_TIMESTAMP = "mock_timestamp"

        assistant = ElectionAssistant()
        assistant.client = mock_client_instance
        
        response = assistant.get_response_sync("How do I vote?", [])
        
        self.assertEqual(response, "This is a test response.")
        mock_chat.send_message.assert_called_once_with("How do I vote?")
        
        # Verify Firestore logging
        mock_db.collection.assert_called_with("chat_logs")
        mock_collection.document.assert_called()
        mock_document.set.assert_called_once()
        # Check that timestamp was used
        args, kwargs = mock_document.set.call_args
        self.assertEqual(args[0]["timestamp"], "mock_timestamp")

    def test_api_key_missing(self):
        """Testing: Test fallback behavior when API keys are missing."""
        with patch.dict(os.environ, {}, clear=True):
            assistant = ElectionAssistant()
            assistant.client = None
            response = assistant.get_response_sync("Hello", [])
            self.assertIn("System Offline", response)

    @patch('app.ElectionAssistant.get_response_sync')
    def test_predict_async_wrapper(self, mock_sync):
        """Efficiency/Testing: Verify async predictability."""
        mock_sync.return_value = "Async test response"
        result = asyncio.run(predict("Test message", []))
        self.assertEqual(result, "Async test response")

if __name__ == '__main__':
    unittest.main()
