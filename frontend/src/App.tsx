import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LayoutDashboard, Flame, Settings, FileText, Bell } from 'lucide-react';
import './App.css';

interface Subnet {
  netuid: number;
  name: string;
  alpha_price: number;
  registration_cost: number;
  ema: number;
  is_immune: boolean;
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [subnets, setSubnets] = useState<Subnet[]>([]);
  const [sortBy, setSortBy] = useState('id');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/subnets');
      setSubnets(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const sortedSubnets = [...subnets].sort((a, b) => {
    if (sortBy === 'id') return a.netuid - b.netuid;
    if (sortBy === 'ema') return b.ema - a.ema;
    if (sortBy === 'price') return b.alpha_price - a.alpha_price;
    return 0;
  });

  return (
    <div className="layout">
      <div className="sidebar">
        <h2>wangye-ge</h2>
        <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
          <LayoutDashboard size={20} /> 看板
        </div>
        <div className={`nav-item ${activeTab === 'racing' ? 'active' : ''}`} onClick={() => setActiveTab('racing')}>
          <Flame size={20} /> 赛马机制
        </div>
        <div className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
          <Settings size={20} /> 系统设置
        </div>
        <div className={`nav-item ${activeTab === 'logs' ? 'active' : ''}`} onClick={() => setActiveTab('logs')}>
          <FileText size={20} /> 运行日志
        </div>
      </div>

      <div className="main-content">
        {activeTab === 'dashboard' && (
          <>
            <div className="controls">
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="id">按 ID 排序</option>
                <option value="ema">按 EMA 排序</option>
                <option value="price">按价格排序</option>
              </select>
            </div>
            <div className="card-grid">
              {sortedSubnets.map((s) => (
                <div key={s.netuid} className="subnet-card">
                  <h3>{s.name} (SN{s.netuid})</h3>
                  <div className="price">τ{s.alpha_price.toFixed(4)}</div>
                  <div className="meta">
                    <div>注册成本: {s.registration_cost.toFixed(2)}</div>
                    <div>EMA: {s.ema.toFixed(4)}</div>
                    <div style={{color: s.is_immune ? 'green' : 'red'}}>
                      {s.is_immune ? '免疫期内' : '非免疫期'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
        
        {activeTab === 'settings' && (
           <div className="settings-page">
              <h2>系统设置</h2>
              {/* Settings implementation here */}
              <p>API 池和 TG 机器人设置在此处管理。</p>
           </div>
        )}
      </div>
    </div>
  );
}

export default App;
