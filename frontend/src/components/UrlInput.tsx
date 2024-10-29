import React, { useState } from 'react';

interface UrlInputProps {
  onSubmit: (url: string) => void;
}

const UrlInput: React.FC<UrlInputProps> = ({ onSubmit }) => {
  const [url, setUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url) {
      onSubmit(url);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="input-container">
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Enter a URL"
      />
      <button type="submit">Submit</button>
    </form>
  );
};

export default UrlInput;
