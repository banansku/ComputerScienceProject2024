import React, { useState } from 'react';

interface Message {
  text: string;
  from: 'user' | 'system';
}

interface ChatViewProps {
  data: { content: string } | null;
}

const ChatView: React.FC<ChatViewProps> = ({ data }) => {
  const [messages, setMessages] = useState<Message[]>([
    { text: 'Welcome to the chat!', from: 'system' },
  ]);
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim()) {
      setMessages([...messages, { text: input, from: 'user' }]);
      setInput('');
    }
  };

  return (
    <div className="chat-container">
      {messages.map((msg, index) => (
        <div key={index} className={`message ${msg.from}`}>
          {msg.text}
        </div>
      ))}
      <div className="input-container">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message"
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
};

export default ChatView;
