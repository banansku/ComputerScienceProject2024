import axios from 'axios';
import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import { UrlData } from '../App';

interface Message {
  text: string;
  from: 'user' | 'system';
}

interface ChatViewProps {
  data: { content: string } | null;
}

const socket = io('http://localhost:5000'); // Connect to the server

const ChatView: React.FC<ChatViewProps> = ({ data }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');

  useEffect(() => {
    // Listen for messages from the server
    socket.on('message', (message: Message) => {
      const appendable: Message = {text: message.text, from: 'system'}
      setMessages((prevMessages) => [...prevMessages, appendable]);
    });

    return () => {
      socket.off('message'); // Clean up the event listener on component unmount
    };
  }, []);

  const handleSend = async () => {
    if (input.trim()) {
      const newMessage: Message = { text: input, from: 'user' };
      
      setMessages([...messages, newMessage]);
      setInput('');

      await axios.post('http://localhost:5000/api/ask_question', { question: input });
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
