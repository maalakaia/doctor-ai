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

  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [selectedValue, setSelectedValue] = useState(null);

  const sendAnswer = async (answer) => {
    const trimmedAnswer = String(answer).trim();

    if (!trimmedAnswer) {
      return;
    }

    // Show the user's answer in the conversation
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: "user",
        text: trimmedAnswer,
      },
    ]);

    // Clear the current interactive question
    setCurrentQuestion(null);
    setSelectedValue(null);

    try {
      const response = await fetch(
        `/api/chat?message=${encodeURIComponent(trimmedAnswer)}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();

      // Store the new AI question
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "ai",
          text: data.question,
        },
      ]);

      // Store the UI information for the new question
      setCurrentQuestion(data);
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

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!message.trim()) {
      return;
    }

    await sendAnswer(message);
    setMessage("");
  };

  const handleChoice = (choice) => {
    setSelectedValue(choice);
  };

  const handleMultipleChoice = (choice) => {
    setSelectedValue((currentValues) => {
      const values = currentValues || [];

      if (values.includes(choice)) {
        return values.filter((value) => value !== choice);
      }

      return [...values, choice];
    });
  };

  const handleContinue = async () => {
    if (currentQuestion?.input_type === "select_all") {
      if (!selectedValue || selectedValue.length === 0) {
        return;
      }

      await sendAnswer(selectedValue.join(", "));
      return;
    }

    if (selectedValue === null || selectedValue === "") {
      return;
    }

    await sendAnswer(selectedValue);
  };

  const renderInput = () => {
    if (!currentQuestion) {
      return null;
    }

    if (currentQuestion.input_type === "scale") {
      return (
        <div className="interactive-input">
          <input
            type="range"
            min="0"
            max="10"
            value={selectedValue ?? 5}
            onChange={(event) =>
              setSelectedValue(Number(event.target.value))
            }
          />

          <div className="scale-labels">
            <span>0</span>
            <strong>{selectedValue ?? 5}</strong>
            <span>10</span>
          </div>

          <button type="button" onClick={handleContinue}>
            Continue
          </button>
        </div>
      );
    }

    if (currentQuestion.input_type === "single_choice") {
      return (
        <div className="interactive-input">
          <div className="choice-list">
            {currentQuestion.options?.map((option) => (
              <button
                type="button"
                key={option}
                className={
                  selectedValue === option
                    ? "choice-button selected"
                    : "choice-button"
                }
                onClick={() => handleChoice(option)}
              >
                {option}
              </button>
            ))}
          </div>

          <button type="button" onClick={handleContinue}>
            Continue
          </button>
        </div>
      );
    }

    if (currentQuestion.input_type === "select_all") {
      return (
        <div className="interactive-input">
          <div className="choice-list">
            {currentQuestion.options?.map((option) => {
              const isSelected =
                Array.isArray(selectedValue) &&
                selectedValue.includes(option);

              return (
                <button
                  type="button"
                  key={option}
                  className={
                    isSelected
                      ? "choice-button selected"
                      : "choice-button"
                  }
                  onClick={() => handleMultipleChoice(option)}
                >
                  {isSelected ? "✓ " : ""}
                  {option}
                </button>
              );
            })}
          </div>

          <button type="button" onClick={handleContinue}>
            Continue
          </button>
        </div>
      );
    }

    return (
      <form className="input-area" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Type your answer..."
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />

        <button type="submit">Send</button>
      </form>
    );
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
            Describe your symptoms and I'll ask questions to better
            understand what's going on.
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

      {currentQuestion ? (
        <div className="question-area">
          {renderInput()}
        </div>
      ) : (
        <form className="input-area" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Describe your symptoms..."
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />

          <button type="submit">Send</button>
        </form>
      )}
    </div>
  );
}

export default App;