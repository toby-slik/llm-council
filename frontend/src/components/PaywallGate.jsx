import React, { useState } from 'react';
import { api } from '../api';
import './PaywallGate.css';

export default function PaywallGate({ token }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCheckout = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.createCheckout(token);
      if (res && res.url) {
        window.location.href = res.url;
      } else {
        setError("Failed to initialize checkout.");
      }
    } catch (err) {
      setError(err.message || "An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="paywall-container">
      <div className="paywall-card">
        <h1>Unlock SLIK Creative Effectiveness</h1>
        <p className="subtitle">Get expert AI marketing evaluations instantly.</p>
        
        <div className="features-list">
          <div className="feature-item">
            <span className="feature-icon">✨</span>
            <p>Comprehensive creative insights from 8 AI specialists</p>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🚀</span>
            <p>Immediate turnaround for all your campaigns</p>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔒</span>
            <p>One-time payment unlocks permanent access</p>
          </div>
        </div>

        <div className="pricing">
          <h2>$1,000 AUD</h2>
          <p className="pricing-terms">One-off premium access</p>
        </div>

        {error && <div className="error-message">{error}</div>}

        <button 
          className="checkout-button" 
          onClick={handleCheckout} 
          disabled={loading}
        >
          {loading ? 'Processing...' : 'Buy Now'}
        </button>
      </div>
    </div>
  );
}
