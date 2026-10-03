import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import CodeBlock from "./CodeBlock";

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="markdown-body text-[15.5px] leading-7 text-ink">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const text = String(children).replace(/\n$/, "");
            const isBlock = text.includes("\n") || !!(props as { node?: { type?: string } }).node;
            const lang = /language-(\w+)/.exec(className || "")?.[1];
            if (!isBlock && !lang) {
              return (
                <code className={className} {...props}>
                  {text}
                </code>
              );
            }
            return <CodeBlock language={lang}>{text}</CodeBlock>;
          },
          pre({ children }) {
            // Let CodeBlock handle its own wrapping
            return <>{children}</>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
