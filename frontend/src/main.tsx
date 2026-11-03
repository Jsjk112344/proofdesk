import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [apiStatus, setApiStatus] = useState('Checking local API…');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/health', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('API unavailable');
        const body = await response.json();
        if (body.service !== 'proofdesk' || body.status !== 'scaffold') {
          throw new Error('Unexpected API response');
        }
        setApiStatus('Local API connected');
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setApiStatus('Start the API using the README instructions.');
      });
    return () => controller.abort();
  }, []);

  return (
    <main>
      <p className="status">Development scaffold · Vultr Agent Rush</p>
      <h1>ProofDesk</h1>
      <p className="intro">Research a prospect. Execute a useful demonstration. Prepare an evidenced approach.</p>
      <p>A local CLI now executes and validates synthetic demonstrations in disposable Docker containers. This screen remains a scaffold; live research, model integration and outreach are not implemented.</p>
      <p role="status">{apiStatus}</p>
      <a href="https://github.com/Jsjk112344/proofdesk">View project and build status</a>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
