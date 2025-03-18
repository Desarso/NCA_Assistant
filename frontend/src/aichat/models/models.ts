export interface TextContent {
    type: "text";
    text: string;
  }
  
  //we are just gonna use base64 encoding
export interface ImageContent {
    type: "image_url";
    image_url: string;
  }
  
export interface Message {
    role: string;
    content: (TextContent | ImageContent)[] | String;
    reasoning?: string;
  }


  export enum PartType {
    TEXT = 1,
    IMAGE_URL = 2,
    TOOL_CALL = 3,
    TOOL_RESPONSE = 4
  }

  export interface Part {
    type: PartType;
    content: string;
  }

  export interface MessageWithParts {
    role: string;
    parts: Part[];
  }