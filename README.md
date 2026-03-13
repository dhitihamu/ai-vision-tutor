# 🎓 Real-Time AI Vision Tutor

A low-latency, real-time multimodal AI tutor powered by the Gemini Live API. This agent doesn't just talk to you—it **sees** your homework, code, and screen in real-time, offering verbal guidance without just giving away the answers.



## ✨ Features
* **Real-Time Voice Conversation:** Fluid, natural back-and-forth audio using Gemini's native audio dialog models.
* **Live Vision Processing:** Multiplexes a 1 FPS video feed over WebSockets so the AI can "see" what you are looking at.
* **Hardware-Optimized Audio:** Utilizes modern `AudioWorklet` processing and hardware echo cancellation to prevent AI audio looping and feedback.
* **Resilient Proxy Architecture:** An auto-reconnecting backend proxy that maintains the user's frontend connection even if the experimental AI backend completes its conversational turn.
* **Camera Toggle:** Bandwidth-saving UI allowing users to pause the vision feed while maintaining the voice call.
* **Dark/Light Mode:** A polished, responsive UI.

## 🛠️ Tech Stack
* **Backend:** Python 3.11, FastAPI, Uvicorn, WebSockets.
* **AI Integration:** Google GenAI SDK (`v1alpha` tier), `gemini-2.5-flash-native-audio-preview-12-2025` model.
* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Web Audio API, `getUserMedia`.
* **Deployment:** Docker, Google Cloud Run.

## 🚀 How It Works (The Architecture)
Because the Gemini Live API requires a highly specific WebSocket connection, this app uses a **Backend Proxy Pattern**. 
1. The browser captures audio (binary PCM) and video frames (base64 JSON).
2. It sends both over a single WebSocket to the FastAPI backend.
3. The FastAPI router separates the binary audio from the text-based video frames.
4. It streams these simultaneously into the Gemini Live API using the `v1alpha` multimodal endpoints.
5. The AI's audio response is streamed back as binary chunks, buffered sequentially in the browser, and played through the Web Audio API without UI freezing.

## 💻 Spin-Up Instructions (Reproducibility)

### Deploy to Google Cloud Run
This project is containerized and ready to be deployed instantly to Google Cloud Run. 

1. Ensure you have the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated.
2. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
3. Run the following command in the root directory, replacing `YOUR_API_KEY` with your actual key:

\`\`\`bash
gcloud run deploy live-agent-app \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="YOUR_API_KEY"
\`\`\`