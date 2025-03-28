import { useEffect, useState } from "react";
import Prism from "prismjs";
import componentsJson from "./components.json";


const components = componentsJson as any;
const HOST = import.meta.env.VITE_CHAT_HOST;


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



export default function CustomPre({ children }: any) {
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
  