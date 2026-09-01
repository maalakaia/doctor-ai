import { useState } from "react";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "ai",
      text: "Hi! Tell me what symptoms you're experiencing, and we'll start there.",
    },
  ]);

  const handleSubmit = async (event) => {
  event.preventDefault();

  const trimmedMessage = message.trim();

  if (!trimmedMessage) {
    return;
  }

  setMessages((currentMessages) => [
    ...currentMessages,
    {
      role: "user",
      text: trimmedMessage,
    },
  ]);

  setMessage("");

  try {
    const response = await fetch(
      `/api/chat?message=${encodeURIComponent(trimmedMessage)}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: "ai",
        text: data.response,
      },
    ]);
  } catch (error) {
    console.error("Error contacting backend:", error);

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: "ai",
        text: "Sorry, I couldn't connect to the server.",
      },
    ]);
  }
};

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Doctor AI</h1>
          <p>Your health assessment assistant</p>
        </div>
      </header>

      <main className="chat-container">
        <div className="welcome-message">
          <h2>How are you feeling?</h2>
          <p>
            Describe your symptoms and I'll ask questions to better understand
            what's going on.
          </p>
        </div>

        <div className="messages">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message ${
                msg.role === "user" ? "user-message" : "ai-message"
              }`}
            >
              <strong>{msg.role === "user" ? "You" : "Doctor AI"}</strong>
              <p>{msg.text}</p>
            </div>
          ))}
        </div>
      </main>

      <form className="input-area" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Describe your symptoms..."
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />

        <button type="submit">Send</button>
      </form>
    </div>
  );
}

export default App;