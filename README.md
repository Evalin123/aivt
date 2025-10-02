# AI VTuber

An AI-powered virtual character chat system that integrates Google Gemini AI with VTube Studio for interactive VTuber experiences. The system features text-to-speech capabilities using ElevenLabs and real-time character animations.

## Features

-   **AI Chat Integration**: Powered by Google Gemini 2.0 Flash for natural conversations
-   **Character Customization**: Load character personalities from text files
-   **Voice Synthesis**: Text-to-speech using ElevenLabs with multilingual support
-   **VTube Studio Integration**: Real-time character animations and expressions
-   **Dual Interface**: Command-line text mode and GUI chat interface
-   **Audio Output**: Configurable audio routing for streaming setups

## Prerequisites

-   Python 3.8 or higher
-   VTube Studio (with API enabled)
-   Google Gemini API key
-   ElevenLabs API key
-   macOS (optimized for macOS audio routing)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd aivt
```

2. Install required dependencies:

```bash
pip3 install google-genai opencv-python pyaudio pillow mss websockets pygame elevenlabs python-dotenv
```

3. Set up environment variables:
   Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

## Setup

### VTube Studio Configuration

1. Open VTube Studio
2. Go to Settings → API
3. Enable "Allow API connections"
4. Note the default port (8001)

### Character Configuration

Place character personality files in the `character_files/` directory. Each `.txt` file should contain:

-   Character name and personality description
-   Communication style guidelines
-   Language preferences
-   Response formatting rules

Example character file (`character_files/Mira.txt`):

```
You are Mira, a lively high school girl who loves sharing fun and laughter with everyone...
```

## Usage

### Chat Mode (GUI Interface)

```bash
python main.py --mode chat
```

This launches a graphical chat interface where you can:

-   Type messages in the text field
-   Send messages to interact with the AI character
-   Hear AI responses through text-to-speech
-   See character animations in VTube Studio

### Text Mode (Command Line)

```bash
python main.py --mode text
```

This provides a command-line interface for text-only conversations.

## Project Structure

```
aivt/
├── main.py              # Main application entry point
├── VTSController.py     # VTube Studio API integration
├── waifu.py            # Chat interface and voice synthesis
├── character_files/    # Character personality definitions
│   └── Mira.txt       # Example character file
├── .env               # Environment variables (create this)
└── README.md          # This file
```

## API Integration

### Google Gemini

-   Uses Gemini 2.0 Flash for AI conversations
-   Supports context-aware responses
-   Handles character personality integration

### ElevenLabs

-   Text-to-speech synthesis
-   Multilingual voice support
-   High-quality audio output

### VTube Studio

-   WebSocket API connection
-   Expression triggering
-   Hotkey automation
-   Real-time character control

## Audio Configuration

The system is optimized for macOS audio routing:

-   Audio outputs to the system default device
-   Compatible with VB-CABLE for streaming setups
-   Uses pygame for cross-platform audio playback

## Troubleshooting

### VTS Connection Issues

-   Ensure VTube Studio is running
-   Check API settings are enabled
-   Verify port 8001 is available
-   Check firewall settings

### Audio Issues

-   Verify ElevenLabs API key is valid
-   Check audio device permissions
-   Ensure pygame is properly installed

### Character Not Responding

-   Check character files in `character_files/`
-   Verify Gemini API key is valid
-   Check internet connection

## Development

### Adding New Characters

1. Create a new `.txt` file in `character_files/`
2. Define character personality and behavior
3. Restart the application to load the new character

### Customizing Voice

Modify the voice settings in `waifu.py`:

```python
voice_id="cgSgspJ2msm6clMCkdW9"  # Change voice ID
model_id="eleven_multilingual_v2"  # Change model
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:

-   Check the troubleshooting section
-   Review API documentation for Gemini and ElevenLabs
-   Ensure VTube Studio is properly configured

