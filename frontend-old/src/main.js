import './style.css'
import heroImg from './assets/hero.png'
import javascriptLogo from './assets/javascript.svg'
import viteLogo from './assets/vite.svg'
import { setupCounter } from './counter.js'

document.querySelector('#app').innerHTML = `
<section id="center">
  <div class="hero">
    <img src="${heroImg}" class="base" width="170" height="179">
    <img src="${javascriptLogo}" class="framework" alt="JavaScript logo"/>
    <img src="${viteLogo}" class="vite" alt="Vite logo" />
  </div>
  <div>
    <h1>Get started</h1>
    <p>Edit <code>src/main.js</code> and save to test <code>HMR</code></p>
  </div>
  <button id="counter" type="button" class="counter"></button>
</section>

<div class="ticks"></div>

<section id="next-steps">
  <div id="docs">
    <svg class="icon" role="presentation" aria-hidden="true"><use href="/icons.svg#documentation-icon"></use></svg>
    <h2>Documentation</h2>
    <p>Your questions, answered</p>
    <ul>
      <li>
        <a href="https://vite.dev/" target="_blank">
          <img class="logo" src="${viteLogo}" alt="" />
          Explore Vite
        </a>
      </li>
      <li>
        <a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript" target="_blank">
          <img class="button-icon" src="${javascriptLogo}" alt="">
          Learn more
        </a>
      </li>
    </ul>
  </div>
  <div id="social">
    <svg class="icon" role="presentation" aria-hidden="true"><use href="/icons.svg#social-icon"></use></svg>
    <h2>Connect with us</h2>
    <p>Join the Vite community</p>
    <ul>
      <li><a href="https://github.com/vitejs/vite" target="_blank"><svg class="button-icon" role="presentation" aria-hidden="true"><use href="/icons.svg#github-icon"></use></svg>GitHub</a></li>
      <li><a href="https://chat.vite.dev/" target="_blank"><svg class="button-icon" role="presentation" aria-hidden="true"><use href="/icons.svg#discord-icon"></use></svg>Discord</a></li>
      <li><a href="https://x.com/vite_js" target="_blank"><svg class="button-icon" role="presentation" aria-hidden="true"><use href="/icons.svg#x-icon"></use></svg>X.com</a></li>
      <li><a href="https://bsky.app/profile/vite.dev" target="_blank"><svg class="button-icon" role="presentation" aria-hidden="true"><use href="/icons.svg#bluesky-icon"></use></svg>Bluesky</a></li>
    </ul>
  </div>
</section>

<div class="ticks"></div>
<section id="spacer"></section>
`

setupCounter(document.querySelector('#counter'))
import "./style.css";

const app = document.querySelector("#app");

app.innerHTML = `
  <div class="app">
    <header class="header">
      <h1>Doctor AI</h1>
      <p>Your personal health assessment assistant</p>
    </header>

    <main class="chat-container">
      <div class="welcome-message">
        <h2>How are you feeling?</h2>
        <p>
          Describe your symptoms and I'll ask you some questions
          to better understand what's going on.
        </p>
      </div>

      <div class="messages" id="messages">
        <div class="message ai-message">
          <strong>Doctor AI</strong>
          <p>
            Hi! Tell me what symptoms you're experiencing, and we'll start there.
          </p>
        </div>
      </div>
    </main>

    <form class="input-area" id="chat-form">
      <input
        type="text"
        id="message-input"
        placeholder="Describe your symptoms..."
        autocomplete="off"
      />
      <button type="submit">Send</button>
    </form>
  </div>
`;

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = input.value.trim();

  if (!message) {
    return;
  }

  const userMessage = document.createElement("div");
  userMessage.className = "message user-message";

  userMessage.innerHTML = `
    <strong>You</strong>
    <p>${message}</p>
  `;

  messages.appendChild(userMessage);

  input.value = "";

  const loadingMessage = document.createElement("div");
  loadingMessage.className = "message ai-message";
  loadingMessage.innerHTML = `
    <strong>Doctor AI</strong>
    <p>Thinking...</p>
  `;

  messages.appendChild(loadingMessage);

  try {
    const response = await fetch(
      `http://localhost:8000/chat?message=${encodeURIComponent(message)}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();

    loadingMessage.innerHTML = `
      <strong>Doctor AI</strong>
      <p>${data.response}</p>
    `;
  } catch (error) {
    console.error("Error contacting backend:", error);

    loadingMessage.innerHTML = `
      <strong>Doctor AI</strong>
      <p>Sorry, something went wrong while contacting the server.</p>
    `;
  }
});