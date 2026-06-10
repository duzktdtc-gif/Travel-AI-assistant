import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Bot, CheckCircle2, Loader2, Plane, RefreshCcw, Send, UserRound, XCircle } from 'lucide-react';
import { resumeChat, sendChat } from './api';

function createId() {
  return crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
}

function MessageBubble({ role, content }) {
  const isUser = role === 'user';

  return (
    <div className={`message ${isUser ? 'message-user' : 'message-ai'}`}>
      <div className="avatar">
        {isUser ? <UserRound size={18} /> : <Bot size={18} />}
      </div>

      <div className="bubble">
        {isUser ? (
          <pre>{content}</pre>
        ) : (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

function ApprovalCard({ interrupt, onApprove, onReject, loading }) {
  const [feedback, setFeedback] = useState('');

  return (
    <div className="approval-card">
      <div className="approval-header">
        <CheckCircle2 size={20} />
        <div>
          <h3>Cần xác nhận của người dùng</h3>
          <p>{interrupt?.question}</p>
        </div>
      </div>

      <div className="approval-preview markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {interrupt?.itinerary || 'Không có nội dung preview.'}
            </ReactMarkdown>
        </div>

      <textarea
        placeholder="Nếu chưa đồng ý, nhập góp ý để agent lập lại kế hoạch..."
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
      />

      <div className="approval-actions">
        <button disabled={loading} className="btn btn-secondary" onClick={() => onReject(feedback)}>
          {loading ? <Loader2 className="spin" size={16} /> : <XCircle size={16} />}
          Chưa đồng ý, lập lại
        </button>
        <button disabled={loading} className="btn btn-primary" onClick={() => onApprove()}>
          {loading ? <Loader2 className="spin" size={16} /> : <CheckCircle2 size={16} />}
          Đồng ý kế hoạch
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [threadId, setThreadId] = useState(() => localStorage.getItem('travel_thread_id') || createId());
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Xin chào! Hãy nhập yêu cầu chuyến đi. Ví dụ: Plan a 5-day trip from Hanoi to Tokyo from 2026-07-02 to 2026-07-06, budget $1500, 2 people, food and anime.'
    }
  ]);
  const [input, setInput] = useState('');
  const [interrupt, setInterrupt] = useState(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('travel_thread_id', threadId);
  }, [threadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, interrupt, loading]);

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  async function handleSend(e) {
    e.preventDefault();
    if (!canSend) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);
    setInterrupt(null);
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    try {
      const data = await sendChat({ message: userMessage, threadId });
      setThreadId(data.thread_id);
      if (data.status === 'requires_approval') {
        setInterrupt(data.interrupt);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Mình đã tạo bản nháp kế hoạch. Vui lòng xem và xác nhận ở khung bên dưới.'
          }
        ]);
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.answer || 'Không có phản hồi.' }]);
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Lỗi: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleResume(approved, feedback = '') {
    setLoading(true);
    try {
      const data = await resumeChat({ threadId, approved, feedback });
      if (data.status === 'requires_approval') {
        setInterrupt(data.interrupt);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: approved ? 'Đang chờ xác nhận tiếp theo.' : 'Mình đã lập lại kế hoạch theo góp ý. Vui lòng kiểm tra bản mới.'
          }
        ]);
      } else {
        setInterrupt(null);
        setMessages((prev) => [...prev, { role: 'assistant', content: data.answer || 'Đã hoàn tất.' }]);
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Lỗi: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  function resetChat() {
    const id = createId();
    setThreadId(id);
    setInterrupt(null);
    setMessages([
      {
        role: 'assistant',
        content:
          'Đã tạo cuộc trò chuyện mới. Hãy nhập điểm đi, điểm đến, ngày đi/về, ngân sách và sở thích.'
      }
    ]);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Plane size={28} />
          <div>
            <h1>Travel AI</h1>
            <span>FastAPI + React + LangGraph</span>
          </div>
        </div>
        <div className="info-card">
          <h2>Multi-Agent Supervisor</h2>
          <p>Research Agent, Weather Agent, Flight/Hotel Agent, Itinerary Agent, Reflection Agent và Human Approval.</p>
        </div>
        <button className="btn btn-secondary full" onClick={resetChat}>
          <RefreshCcw size={16} />
          New thread
        </button>
        <p className="thread-id">Thread: {threadId}</p>
      </aside>

      <main className="chat-panel">
        <div className="messages">
          {messages.map((m, idx) => (
            <MessageBubble key={`${m.role}-${idx}`} role={m.role} content={m.content} />
          ))}
          {loading && (
            <div className="message message-ai">
              <div className="avatar"><Bot size={18} /></div>
              <div className="bubble loading"><Loader2 className="spin" size={18} /> Agent đang xử lý...</div>
            </div>
          )}
          {interrupt && (
            <ApprovalCard
              interrupt={interrupt}
              loading={loading}
              onApprove={() => handleResume(true, '')}
              onReject={(feedback) => handleResume(false, feedback)}
            />
          )}
          <div ref={bottomRef} />
        </div>

        <form className="composer" onSubmit={handleSend}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="VD: Lập lịch trình từ Hà Nội đến Tokyo 2026-07-02 đến 2026-07-06, ngân sách $1500..."
          />
          <button className="btn btn-primary" disabled={!canSend} type="submit">
            <Send size={16} />
            Send
          </button>
        </form>
      </main>
    </div>
  );
}
