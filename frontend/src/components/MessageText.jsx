import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const markdownComponents = {
  table: ({ children }) => (
    <div className="markdown-table-wrap">
      <table>{children}</table>
    </div>
  ),
};

export default function MessageText({ content, markdown = false, className = "message-text" }) {
  if (markdown) {
    return (
      <div className={`${className} markdown-body`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {content}
        </ReactMarkdown>
      </div>
    );
  }

  return <p className={className}>{content}</p>;
}
