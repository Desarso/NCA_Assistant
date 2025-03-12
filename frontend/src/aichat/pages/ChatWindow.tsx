import { useState, useRef, useEffect, FormEvent } from 'react';
import ReactMarkdown from 'react-markdown';
import WaveIcon from './WaveIcon';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

import Prism from 'prismjs'
// import 'prismjs/components/prism-python'
import './index.css';
import { Message } from '../models/models';
import componentsJson from './components.json';

const components = componentsJson as any;
const HOST = import.meta.env.VITE_CHAT_HOST;

// Client-side language registry
const loadedLanguages: { [key: string]: boolean } = {
  markup: true,     // HTML, XML, SVG, MathML...
  HTML: true,
  XML: true,
  SVG: true,
  MathML: true,
  SSML: true,
  Atom: true,
  RSS: true,
  css: true,
  'c-like': true,
  javascript: true,  // IMPORTANT: Use 'javascript' not 'js'
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
    const { authFetch } = await import('@/lib/utils');
    
    const response = await authFetch(`${HOST}/api/prism-language?name=${language}`);
    if (!response.ok) {
      throw new Error(
        `Failed to fetch language "${language}": ${response.status}`,
      );
    }
    const scriptText = await response.text();

    // console.log("Script: ", language)
    // console.log(scriptText);

    // Execute the script.  Important: This is where the Prism component is registered.
    eval(scriptText); // VERY CAREFUL.  See security notes below.

    loadedLanguages[language] = true;
    // console.log(`Language "${language}" loaded successfully.`);
    Prism.highlightAll();
  } catch (error) {
    console.error(`Error loading language "${language}":`, error);
    // Consider a fallback (e.g., plain text highlighting)
  }
};

function CustomPre({ children }: any) {
  const [copied, setCopied] = useState(false);
  const codeContent = children?.props?.children?.toString() || '';
  const language = children?.props?.className?.replace('language-', '') || '';

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
    <div className="relative bg-gray-100 border border-gray-300 rounded-lg my-4 dark:bg-gray-800 dark:border-gray-600">
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
          className={`icon icon-tabler icons-tabler-outline icon-tabler-copy transition-all duration-200 ${copied ? 'scale-75' : 'scale-100'}`}
        >
          <path stroke="none" d="M0 0h24v24H0z" fill="none" />
          <path d="M7 7m0 2.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667z" />
          <path d="M4.012 16.737a2.005 2.005 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1" />
        </svg>
        <span
          className={`transition-all duration-200 ${copied ? 'text-sm' : 'text-xs'} dark:text-gray-400`}
        >
          {copied ? 'Copied!' : 'Copy'}
        </span>
      </button>
      <pre className="overflow-x-auto dark:text-gray-100">{children}</pre>
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
    .map(message => {
      try {
        const parsed = JSON.parse(message.content);
        
        // Handle model requests
        if (parsed.type === "model_request") {
          // Find the UserPromptPart in the parts array
          const userPart = parsed.parts.find((part: any) => part.type === "UserPromptPart");
          if (userPart) {
            return {
              role: "user",
              content: userPart.content
            };
          }
          const toolReturnPart = parsed.parts.find((part: any) => part.type === "ToolReturnPart");
          if (toolReturnPart) {
            return {
              role: "tool_response",
              content: JSON.stringify(toolReturnPart.content)
            };
          }
          return null;
        }
        
        // Handle model responses
        if (parsed.type === "model_response") {
          if (parsed.parts[0].type === "TextPart") {
            return {
              role: "assistant",
              content: parsed.parts[0].content
            };
          }
          if (parsed.parts[0].type === "ToolCallPart") {
            return {
              role: "tool_call",
              content: JSON.stringify(parsed.parts[0].content)
            };
          }
          return null;
        }
        
        return null;
      } catch (e) {
        console.error("Error parsing message:", e);
        return null;
      }
    })
    .filter((message): message is ChatMessage => message !== null);
}





function ChatWindow({ id }: { id?: string }) {
  const [gettingResponse, setGettingResponse] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [isListening, setIsListening] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [conversationId, _] = useState<string>(id || crypto.randomUUID().toString());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

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



  const handleSubmit = async (e: FormEvent) => {
    if (window.location.pathname === '/') {
      window.history.pushState({}, '', `/chat/${conversationId}`);
    }
    
    e.preventDefault();
    if (gettingResponse) return;

    if (input.trim()) {
        const newMessage: Message = {
            role: 'user',
            content: input,
        };

        setInput('');
        setGettingResponse(true);

        messages.push(newMessage);
        scrollToBottom();

        const url = new URL(`${HOST}/chat`);
        url.searchParams.append('prompt', input);
        console.log(conversationId);
        url.searchParams.append('conversation_id', conversationId);

        try {
            // Import authFetch to add auth token to the request
            const { authFetch } = await import('@/lib/utils');
            
            const response = await authFetch(url.toString(), {
                method: 'POST',
                headers: {
                    'Accept': 'text/event-stream',
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            if (!response.body) {
                throw new Error('Response body is null');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let assistantMessage: Message = {
                role: 'assistant',
                content: '',
            };
            messages.push(assistantMessage);

            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process complete SSE messages from buffer
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || ''; // Keep the last incomplete chunk in the buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonString = line.slice(6); // Remove 'data: ' prefix
                            const data = JSON.parse(jsonString);
                            console.log(data);
                            
                            if (data.type === 'part_start') {
                                messages[messages.length - 1].content += data.data.part.content;
                            } else if (data.type === 'part_delta') {
                                messages[messages.length - 1].content += data.data.delta.content;
                            } else if (data.type === 'tool_call') {
                                console.log('Tool call:', data);
                            }
                            
                            setMessages([...messages]); // Trigger re-render
                        } catch (e) {
                            console.error('Error parsing JSON:', e);
                        }
                    }
                }
            }

        } catch (error) {
            console.error('Error sending message:', error);
        } finally {
            setGettingResponse(false);
        }
    }
};

  const fetchMessageHistory = async () => {
    const url = new URL(`${HOST}/conversations/${conversationId}/messages`);
    try {
      // Import here to avoid circular dependency
      const { authFetch } = await import('@/lib/utils');
      
      const response = await authFetch(url.toString(), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log(data.messages);
      const chatMessages = convertToChatMessages(data.messages);
      console.log(chatMessages);
      // console.log(data);
      setMessages(chatMessages);
    } catch (error) {
      console.error('Failed to fetch chat history:', error);
    }
  };

  const handleFileAttachment = () => {
    console.log('File attachment initiated');
  };

  const toggleListening = () => {
    if (input.trim() === '') {
      setIsListening(!isListening);
    } else {
      handleSubmit({ preventDefault: () => {} } as FormEvent); // Mock event object
    }
  };

  return (
    <div className="Chat-Container h-full w-full relative flex align-center justify-center chatMessages max-h-[calc(100vh-88px)]
      md:max-h-[calc(100vh-44px)]
    ">
      <div className="chat-window">
        {isListening ? (
          // <AudioCircle onClose={() => setIsListening(false)} />
          <></>
        ) : (
          <>
            <div className="chat-messages text-xl! md:text-base!">
              {messages.map((message, index) => (
                message.role === 'user' || message.role === 'assistant' ? (
                  <div key={index} className={`message ${message.role}`}>
                    {message.role === 'user'
                      ? (message.content as string)
                      : message.role === 'assistant' && (
                          <ReactMarkdown
                            components={{
                              pre: CustomPre,
                            }}
                            children={message.content as string}
                            remarkPlugins={[remarkGfm, remarkBreaks]}
                          />
                        )}
                  </div>
                ) : null
              ))}
              <div ref={messagesEndRef} />
            </div>
            <form onSubmit={handleSubmit} className="chat-input">
              <input
                className="text-xl!
                md:text-base!
                "
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
              />
              <div className="button-container">
                <button
                  type="button"
                  className="icon-button"
                  onClick={handleFileAttachment}
                >
                  <i className="fas fa-paperclip"></i>
                </button>
                <button
                  type="button"
                  className="icon-button main-action"
                  onClick={toggleListening}
                >
                  {input.trim() === '' ? (
                    <WaveIcon />
                  ) : (
                    <i className="fas fa-paper-plane"></i>
                  )}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

export default ChatWindow;
