import React, { useState } from 'react';
import axios from 'axios';
import UrlInput from './components/UrlInput';
import ChatView from './components/ChatView';
import './App.css';


export interface UrlData {
  content: string;
}


const App: React.FC = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);

  const handleUrlSubmit = async (url: string) => {
    setIsChatOpen(true)

    try {
      axios.post<UrlData>('http://localhost:5000/api/upload', { video_url: url }).then(() => setIsChatOpen(true))
    } catch (error) {
      console.error("Error processing the URL:", error);
    }
  };

  const resetChat = () => {
    setIsChatOpen(false)
  }

  return (
    <div className="App">
     <div className="form-container">
        {isChatOpen ? <ChatView onResetView={resetChat}/> : <UrlInput onSubmit={handleUrlSubmit} />}
      </div>
    </div>
  );
}

export default App;
