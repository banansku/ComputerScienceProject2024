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
  const [urlData, setUrlData] = useState<UrlData | null>(null);

  const handleUrlSubmit = async (url: string) => {
    setIsChatOpen(true)

    try {
      const response = await axios.post<UrlData>('http://localhost:5000/api/upload', { video_url: url });
      setUrlData(response.data);
      setIsChatOpen(true);
    } catch (error) {
      console.error("Error processing the URL:", error);
    }
  };

  return (
    <div className="App">
     <div className="form-container">
        {isChatOpen ? <ChatView data={urlData} /> : <UrlInput onSubmit={handleUrlSubmit} />}
      </div>
    </div>
  );
}

export default App;
