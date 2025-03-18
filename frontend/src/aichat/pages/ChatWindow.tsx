import { useState, useRef, useEffect, FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import WaveIcon from "./WaveIcon";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import supersub from "remark-supersub";

import Prism from "prismjs";
import "./index.css";
// import 'prismjs/components/prism-python'
import { Message } from "../models/models";
import componentsJson from "./components.json";
import MicrophoneVisualizer from "../../components/MicrophoneVisualizer";
import { useSidebar } from "@/components/ui/sidebar";
import { useChatContext } from "@/layout";
import { useParams } from "react-router-dom";

const components = componentsJson as any;
const HOST = import.meta.env.VITE_CHAT_HOST;

// Client-side language registry
const loadedLanguages: { [key: string]: boolean } = {
  markup: true, // HTML, XML, SVG, MathML...
  HTML: true,
  XML: true,
  SVG: true,
  MathML: true,
  SSML: true,
  Atom: true,
  RSS: true,
  css: true,
  "c-like": true,
  javascript: true, // IMPORTANT: Use 'javascript' not 'js'
};

const loadLanguage = async (language: string) => {
  if (loadedLanguages[language]) {
    return; // Already loaded
  }

  try {
    const languageData = components.languages[language];

    if (!languageData) {
      console.warn(`Language "${language}" not found in components.json.`);
      return;
    }

    // Load required languages recursively BEFORE loading the target language
    if (languageData.require) {
      const requirements = Array.isArray(languageData.require)
        ? languageData.require
        : [languageData.require];

      for (const requirement of requirements) {
        await loadLanguage(requirement);
      }
    }

    // Import authFetch to add auth token to the request
    const { authFetch } = await import("@/lib/utils");

    const response = await authFetch(
      `${HOST}/api/prism-language?name=${language}`
    );
    if (!response.ok) {
      throw new Error(
        `Failed to fetch language "${language}": ${response.status}`
      );
    }
    const scriptText = await response.text();


    // Execute the script.  Important: This is where the Prism component is registered.
    eval(scriptText); // VERY CAREFUL.  See security notes below.

    loadedLanguages[language] = true;
    Prism.highlightAll();
  } catch (error) {
    console.error(`Error loading language "${language}":`, error);
    // Consider a fallback (e.g., plain text highlighting)
  }
};

function CustomPre({ children }: any) {
  const [copied, setCopied] = useState(false);
  const codeContent = children?.props?.children?.toString() || "";
  const language = children?.props?.className?.replace("language-", "") || "";

  useEffect(() => {
    // console.log(language, " detected")
    if (language && !loadedLanguages[language]) {
      loadLanguage(language); // Load the language if it's not already loaded.
    }
  }, [language]);

  const handleCopy = () => {
    navigator.clipboard.writeText(codeContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative bg-gray-100 border border-gray-300 rounded-lg my-4 dark:bg-gray-800 dark:border-gray-600 p-0 m-0">
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 text-gray-600 text-xs p-2 rounded hover:text-gray-800 transition flex items-center gap-1 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`icon icon-tabler icons-tabler-outline icon-tabler-copy transition-all duration-200 ${
            copied ? "scale-75" : "scale-100"
          }`}
        >
          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
          <path d="M7 7m0 2.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667z" />
          <path d="M4.012 16.737a2.005 2.005 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1" />
        </svg>
        <span
          className={`transition-all duration-200 ${
            copied ? "text-sm" : "text-xs"
          } dark:text-gray-400`}
        >
          {copied ? "Copied!" : "Copy"}
        </span>
      </button>
      <pre className="overflow-x-auto dark:text-gray-100 p-4 whitespace-pre-wrap break-words">
        {children}
      </pre>
    </div>
  );
}

interface ChatMessage {
  role: string;
  content: string;
}

interface DBMessage {
  id: number;
  created_at: string;
  conversation_id: number;
  content: string;
  is_user_message: boolean;
  updated_at: string;
}

function convertToChatMessages(messages: DBMessage[]): ChatMessage[] {
  return messages
    .map((message) => {
      try {
        const parsed = JSON.parse(message.content);

        // Handle model requests
        if (parsed.type === "model_request") {
          // Find the UserPromptPart in the parts array
          const userPart = parsed.parts.find(
            (part: any) => part.type === "UserPromptPart"
          );
          if (userPart) {
            return {
              role: "user",
              content: userPart.content,
            };
          }
          const toolReturnPart = parsed.parts.find(
            (part: any) => part.type === "ToolReturnPart"
          );
          if (toolReturnPart) {
            return {
              role: "tool_response",
              content: JSON.stringify(toolReturnPart.content),
            };
          }
          return null;
        }

        // Handle model responses
        if (parsed.type === "model_response") {
          //to rerturn
          let result = {
            role: "assistant",
            content: "",
            reasoning: "",
          };

          for (const part of parsed.parts) {
            if (part.type === "TextPart") {
              result.content += part.content;
            }
            if (part.type === "ReasoningPart") {
              result.reasoning += part.content
            }
            if (parsed.parts[0].type === "ToolCallPart") {
              return {
                role: "tool_call",
                content: JSON.stringify(parsed.parts[0].content),
              };
            }
          }

          return result;  
          
        }

        return null;
      } catch (e) {
        console.error("Error parsing message:", e);
        return null;
      }
    })
    .filter((message): message is ChatMessage => message !== null);
}

// Create a new ChatInput component
const ChatInput = ({ 
  onSubmit, 
  gettingResponse, 
  handleFileAttachment, 
  setIsListening, 
  handleStopRequest 
}: { 
  onSubmit: (text: string) => void,
  gettingResponse: boolean,
  handleFileAttachment: () => void,
  setIsListening: (isListening: boolean) => void,
  handleStopRequest: () => void
}) => {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSubmit(input);
      setInput("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        className="flex-1 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 px-4 py-2 text-sm md:text-base focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:text-gray-200"
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type your message..."
        autoComplete="off"
        spellCheck="false"
      />
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded-full p-2 text-gray-500 bg-gray-50 hover:bg-gray-100 dark:text-gray-400 dark:bg-gray-800 dark:hover:bg-gray-700"
          onClick={handleFileAttachment}
        >
          <i className="fas fa-paperclip"></i>
        </button>

        {gettingResponse ? (
          <button
            type="button"
            className="rounded-full p-2 text-red-600 bg-gray-100 hover:bg-gray-200 dark:text-red-400 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors min-w-[40px] flex items-center justify-center"
            onClick={handleStopRequest}
          >
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              width="16" 
              height="16" 
              viewBox="0 0 24 24" 
              fill="currentColor"
            >
              <rect x="6" y="6" width="12" height="12" />
            </svg>
          </button>
        ) : input.trim() === "" ? (
          <button
            type="button"
            className="rounded-full p-2 text-gray-600 bg-gray-100 hover:bg-gray-200 dark:text-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors min-w-[40px] flex items-center justify-center"
            onClick={() => setIsListening(true)}
          >
            <WaveIcon />
          </button>
        ) : (
          <button
            type="button"
            className="rounded-full p-2 text-gray-600 bg-gray-100 hover:bg-gray-200 dark:text-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors min-w-[40px] flex items-center justify-center"
            onClick={handleSubmit}
          >
            <i className="fas fa-paper-plane"></i>
          </button>
        )}
      </div>
    </form>
  );
};

function ChatWindow() {
  const { open, openMobile, isMobile } = useSidebar();
  const [gettingResponse, setGettingResponse] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isListening, setIsListening] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const { id } = useParams();
  const [conversationId, setConversationId] = useState<string>(
    id || crypto.randomUUID().toString()
  );
  const [isMuted, setIsMuted] = useState<boolean>(false);

  // Add abort controller ref
  const abortControllerRef = useRef<boolean>(false);
  const { fetchConversations } = useChatContext();

  const scrollToBottom = async () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    console.log("id", id);
    if (id) {
      setConversationId(id);
    }
    (async () => {
      await fetchMessageHistory(id);

      Prism.highlightAll();
    })();

  }, [id])
    


  useEffect(() => {
    scrollToBottom();
    Prism.highlightAll();
  }, [messages]);

  //   //when chats load set messages
  useEffect(() => {
    // load messages based on chat_id 123 and user_id random
    (async () => {
      await fetchMessageHistory();

      Prism.highlightAll();
    })();
  }, []);


  
  const handleSubmit = async (text: string) => {

    if (gettingResponse) return;

    setGettingResponse(true);

    const newMessage: Message = {
      role: "user",
      content: text,
    };

    const updatedMessages = [...messages, newMessage];
    setMessages(updatedMessages);
    await scrollToBottom();

    const url = new URL(`${HOST}/api/v1/chats/chat`);
    url.searchParams.append("prompt", text);
    url.searchParams.append("conversation_id", conversationId);

    try {
      // Reset abort flag at start of new request
      abortControllerRef.current = false;

      // Import authFetch to add auth token to the request
      const { authFetch } = await import("@/lib/utils");

      const response = await authFetch(url.toString(), {
        method: "POST",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let assistantMessage: Message = {
        role: "assistant",
        content: "",
        reasoning: "",
      };
      // Update the messages array with the assistant message
      const newMessages = [...updatedMessages, assistantMessage];
      messages.push(assistantMessage);

      let buffer = "";

      while (true) {
        // Check if request was aborted
        if (abortControllerRef.current) {
          reader.cancel();
          break;
        }

        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages from buffer
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || ""; // Keep the last incomplete chunk in the buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const jsonString = line.slice(6);
              const data = JSON.parse(jsonString);
              // console.log("data:", data);
              // console.log("event kind:", data.type);
              // console.log("data.data:", data.data.part.part_kind);
              if (data.type === "part_start") {
                  // console.log("Part start:", data);
                  if (data.data.part.part_kind === "text") {
                    messages[messages.length - 1].content += data.data.part.content;
                    // console.log("Text part:", data.data.part.content);
                  } else if (data.data.part.part_kind === "reasoning") {
                    messages[messages.length - 1].reasoning += data.data.part.reasoning;
                    // console.log("Reasoning part:", data.data.part.reasoning);
                  }
              } else if (data.type === "part_delta") {
                if (data.data.delta.part_kind === "text") {
                  // console.log("Text delta:", data.data.delta.content);
                  messages[messages.length - 1].content += data.data.delta.content;
                } else if (data.data.delta.part_kind === "reasoning") {
                  // console.log("Reasoning delta:", data.data.delta.reasoning);
                  messages[messages.length - 1].reasoning += data.data.delta.reasoning;
                }
                //await appendContentWithDelay(data.data.delta.content, newMessages);;
                // setMessages([...messages]);
              } else if (data.type === "tool_call") {
                console.log("Tool call:", data);
              }

              setMessages([...newMessages]); // Trigger re-render with the updated array
            } catch (e) {
              console.error("Error parsing JSON:", e);
            }
          }
        }
      }

      if (window.location.pathname === "/") {
        window.history.pushState({}, "", `/chat/${conversationId}`);
        fetchConversations();
      }
  
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setGettingResponse(false);
    }
  };

  const fetchMessageHistory = async (id: string = conversationId) => {
    const url = new URL(`${HOST}/api/v1/chats/conversations/${id}/messages`);
    try {
      // Import here to avoid circular dependency
      const { authFetch } = await import("@/lib/utils");

      const response = await authFetch(url.toString(), {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      // console.log(data.messages);
      const chatMessages = convertToChatMessages(data.messages);
      //console.log(chatMessages);
      // console.log(data);
      setMessages(chatMessages);
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  };

  const handleFileAttachment = () => {
    console.log("File attachment initiated");
  };

  const handleMicrophoneClose = () => {
    if (navigator.mediaDevices) {
      console.log("Stopping microphone");
      // Stop all microphone tracks
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          //print all tracks
          console.log(stream.getTracks());
          stream.getTracks().forEach((track) => track.stop());
        })
        .catch((err) => console.error("Error accessing microphone:", err));
    }
    setIsListening(false);
  };

  const handleMicrophoneMute = () => {
    if (navigator.mediaDevices) {
      // Stop all microphone tracks
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          stream.getTracks().forEach((track) => track.stop());
        })
        .catch((err) => console.error("Error accessing microphone:", err));
    }
    setIsMuted(!isMuted);
  };

  // Update the stop button click handler
  const handleStopRequest = () => {
    abortControllerRef.current = true;
    setGettingResponse(false);
  };

  return (
    <div className="flex h-full w-full flex-col justify-center items-center bg-gray-50 dark:bg-gray-900 ">
      {isListening ? (
        <div className="flex-1 flex items-center justify-center">
          <MicrophoneVisualizer
            isListening={!isMuted}
            onClose={handleMicrophoneClose}
            onMute={handleMicrophoneMute}
          />
        </div>
      ) : (
        <>
          <div
            className={`flex-1 flex flex-col items-center overflow-y-auto p-4 space-y-6 Chat-Container 
            max-h-[calc(100vh-134px)] 
            md:max-h-[calc(100vh-136px)] 
            ${
              isMobile
                ? openMobile
                  ? "w-[calc(100vw-var(--sidebar-width))]"
                  : "w-full"
                : open
                ? "w-[calc(100vw-var(--sidebar-width))]"
                : "w-full"
            }
            `}
          >
            {messages.map((message, index) =>
              message.role === "user" || message.role === "assistant" ? (
                <div
                  key={index}
                  className={`md:max-w-[900px] w-full flex ${
                    message.role === "user"
                      ? "message user justify-end"
                      : "message assistant justify-start"
                  }`}
                >
                  <div
                    className={`${
                      message.role === "user"
                        ? "max-w-[70%] flex items-end self-end"
                        : "w-full"
                    } rounded-lg p-4 ${
                      message.role === "user"
                        ? "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        : "bg-white dark:bg-gray-800 shadow-sm"
                    } break-words overflow-hidden`}
                  >
                    {message.role === "user" ? (
                      <div className="text-sm md:text-base">
                        {message.content as string}
                      </div>
                    ) : (
                      <ReactMarkdown
                        components={{
                          pre: CustomPre,
                        }}
                        children={message.content as string}
                        remarkPlugins={[remarkGfm, remarkBreaks, supersub]}
                        rehypePlugins={[]}
                      />
                    )}
                  </div>
                </div>
              ) : null
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t md:border md:rounded-lg md:mb-4 md:shadow-md border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-800 w-full md:max-w-[900px]">
            <ChatInput 
              onSubmit={handleSubmit}
              gettingResponse={gettingResponse}
              handleFileAttachment={handleFileAttachment}
              setIsListening={setIsListening}
              handleStopRequest={handleStopRequest}
            />
          </div>
        </>
      )}
    </div>
  );
}

export default ChatWindow;
