import { useState } from "@lynx-js/react";

export default function Chatbox() {
  const [messages, setMessages] = useState<{ text: string; sender: string }[]>(
    []
  );
  const [input, setInput] = useState("");

  const mockResponses = [
    "Hello! How can I help you?",
    "That's interesting! Tell me more.",
    "I'm just a simple AI, but I'm listening.",
    "Could you clarify that a bit?",
    "Let's dive deeper into that thought.",
  ];

  const sendMessage = () => {
    console.log("=== Send Message Debug ===");
    console.log("Current input:", input);
    console.log("Current messages:", messages);
    
    if (!input.trim()) {
      console.log("Input is empty, returning");
      return;
    }
    
    const userMessage = { text: input, sender: "user" };
    console.log("Adding user message:", userMessage);
    
    setMessages([...messages, userMessage]);

    // Simulate an AI response after a short delay
    setTimeout(() => {
      const aiResponse = {
        text: mockResponses[Math.floor(Math.random() * mockResponses.length)],
        sender: "ai",
      };
      console.log("Adding AI response:", aiResponse);
      setMessages((prev) => [...prev, aiResponse]);
    }, 500);

    setInput("");
  };

  return (
    <page className="w-full h-[400px] p-5 border-gray-300 rounded-lg">
      <view className="h-[200px] w-80 m-10 pt-10 overflow-scroll border-b mb-2 bg-white">
        {messages.map((msg, idx) => (
          <view
            key={idx}
            className={`p-2 my-1 ${
              msg.sender === "user" 
                ? "bg-blue-200 self-end" 
                : "bg-gray-300 self-start"
            }`}
          >
            <text>{msg.text}</text>
          </view>
        ))}
      </view>
      <view className="w-full flex flex-row">
        <input
          value={input}
          bindtextchange={(e) => {
            console.log("Input changed:", e.detail.value);
            setInput(e.detail.value);
          }}
          className="w-[200px] h-10 px-4 mb-2 text-base rounded-lg border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 transition duration-200"
          placeholder="Type a message..."
        />
        <view
          bindtap={sendMessage}
          className="w-full h-10 px-4 mb-2 text-base rounded-lg border border-gray-300 bg-blue-500 hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition duration-200 flex items-center justify-center"
        >
          <text style={{ color: "white", textAlign: "center" }}>Send</text>
        </view>
      </view>
    </page>
  );
}
