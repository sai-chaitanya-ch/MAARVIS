import { useEffect, useRef } from "react";
import { ChatMessage } from "../lib/api";
import UserMessage from "./UserMessage";
import AssistantMessage from "./AssistantMessage";

export default function MessageList({ messages }: { messages: ChatMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, messages[messages.length - 1]?.content?.length]);

  return (
    <div className="mx-auto w-full max-w-2xl space-y-8 px-4 pb-48 pt-24">
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} content={message.content} />
        ) : (
          <AssistantMessage key={message.id} message={message} />
        )
      )}
      <div ref={endRef} />
    </div>
  );
}
