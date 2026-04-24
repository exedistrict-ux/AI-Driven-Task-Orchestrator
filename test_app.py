import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add current directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import ElectionAssistant

class TestVoteSmart(unittest.TestCase):
    def setUp(self):
        # Mock environment variable
        os.environ["GEMINI_API_KEY"] = "test_key"
        self.assistant = ElectionAssistant()

    def test_assistant_initialization(self):
        """Test if the assistant initializes correctly with an API key."""
        self.assertIsNotNone(self.assistant)
        # In our mock environment, it should have a client if key is set
        # Note: In app.py, if genai.Client fails, it sets self.client to None
        # We'll mock the genai.Client in the next test

    @patch('app.genai.Client')
    def test_get_response_mock(self, mock_genai):
        """Test getting a response with a mocked Gemini client."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_genai.return_value = mock_client_instance
        
        mock_chat = MagicMock()
        mock_client_instance.chats.create.return_value = mock_chat
        
        mock_response = MagicMock()
        mock_response.text = "This is a test response about voting."
        mock_chat.send_message.return_value = mock_response

        # Re-init assistant with mock
        assistant = ElectionAssistant()
        assistant.client = mock_client_instance
        
        response = assistant.get_response("How do I vote?", [])
        
        self.assertEqual(response, "This is a test response about voting.")
        mock_chat.send_message.assert_called_once_with("How do I vote?")

    def test_api_key_missing(self):
        """Test behavior when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Temporarily clear env to test missing key
            assistant = ElectionAssistant()
            assistant.client = None # Explicitly set for test
            response = assistant.get_response("Hello", [])
            self.assertIn("API Key Missing", response)

if __name__ == '__main__':
    unittest.main()
