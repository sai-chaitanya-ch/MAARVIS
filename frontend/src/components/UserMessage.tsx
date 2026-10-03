interface UserMessageProps {
  content: string;
}

export default function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="flex w-full justify-end py-2">
      <div className="max-w-2xl rounded-2xl bg-[#F3F4F6] px-4 py-2.5 text-sm leading-relaxed text-[#111111] shadow-2xs">
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}
