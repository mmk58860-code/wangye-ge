import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LayoutDashboard, Flame, Settings, FileText, LogOut, Plus, Trash2 } from 'lucide-react';
import './App.css';

interface Subnet {
  netuid: number;
  name: string;
  alpha_price: number;
  registration_cost: number;
  ema: number;
  is_immune: boolean;
}

interface ApiKey {
  id: number;
  key_value: string;
  description: string;
  enabled: boolean;
  requests_per_second: number;
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [subnets, setSubnets] = useState<Subnet[]>([]);
  const [sortBy, setSortBy] = useState('id');
  const [token, setToken] = useState(() => localStorage.getItem('adminToken') || '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newApiKey, setNewApiKey] = useState('');
  const [newApiKeyDescription, setNewApiKeyDescription] = useState('');
  const [apiKeyMessage, setApiKeyMessage] = useState('');

  const authHeaders = (authToken = token) => ({ 'X-Admin-Token': authToken });

  useEffect(() => {
    if (!token) return;

    fetchData(token);
    fetchApiKeys(token);
    const interval = setInterval(() => fetchData(token), 10000);
    return () => clearInterval(interval);
  }, [token]);

  const fetchData = async (authToken: string) => {
    try {
      const res = await axios.get('/api/subnets', {
        headers: authHeaders(authToken),
      });
      setSubnets(res.data);
    } catch (err) {
      console.error(err);
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        localStorage.removeItem('adminToken');
        setToken('');
      }
    }
  };

  const fetchApiKeys = async (authToken = token) => {
    if (!authToken) return;

    try {
      const res = await axios.get('/api/api-keys', {
        headers: authHeaders(authToken),
      });
      setApiKeys(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddApiKey = async (event: React.FormEvent) => {
    event.preventDefault();
    setApiKeyMessage('');

    if (!newApiKey.trim()) {
      setApiKeyMessage('请输入 Dwellir API Key');
      return;
    }

    try {
      await axios.post(
        '/api/api-keys',
        {
          key_value: newApiKey.trim(),
          description: newApiKeyDescription.trim() || 'Dwellir API Key',
          requests_per_second: 20,
        },
        { headers: authHeaders() }
      );
      setNewApiKey('');
      setNewApiKeyDescription('');
      setApiKeyMessage('API Key 已添加，后台会自动开始同步数据。');
      fetchApiKeys();
      fetchData(token);
    } catch (err) {
      setApiKeyMessage('添加失败，请检查 Key 是否重复或后端日志。');
    }
  };

  const handleDeleteApiKey = async (keyId: number) => {
    await axios.delete(`/api/api-keys/${keyId}`, {
      headers: authHeaders(),
    });
    fetchApiKeys();
  };

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoginError('');

    try {
      const res = await axios.post('/api/login', { username, password });
      localStorage.setItem('adminToken', res.data.token);
      setToken(res.data.token);
      setPassword('');
    } catch (err) {
      setLoginError('账号或密码不正确');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('adminToken');
    setToken('');
    setSubnets([]);
  };

  const sortedSubnets = [...subnets].sort((a, b) => {
    if (sortBy === 'id') return a.netuid - b.netuid;
    if (sortBy === 'ema') return b.ema - a.ema;
    if (sortBy === 'price') return b.alpha_price - a.alpha_price;
    return 0;
  });

  if (!token) {
    return (
      <div className="login-page">
        <form className="login-panel" onSubmit={handleLogin}>
          <h1>wangye-ge</h1>
          <input
            autoFocus
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="管理员账号"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="管理员密码"
            type="password"
          />
          {loginError && <div className="login-error">{loginError}</div>}
          <button type="submit">登录</button>
        </form>
      </div>
    );
  }

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
        <button className="logout-button" onClick={handleLogout}>
          <LogOut size={18} /> 退出登录
        </button>
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
              {sortedSubnets.length === 0 && (
                <div className="empty-state">
                  <h3>暂无子网数据</h3>
                  <p>请先在系统设置里添加 Dwellir API Key。添加后后台会开始同步，首次显示可能需要等待 1 分钟左右。</p>
                  <button onClick={() => setActiveTab('settings')}>去系统设置</button>
                </div>
              )}
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
              <form className="settings-panel" onSubmit={handleAddApiKey}>
                <h3>Dwellir API Key</h3>
                <input
                  value={newApiKey}
                  onChange={(e) => setNewApiKey(e.target.value)}
                  placeholder="输入 Dwellir API Key"
                />
                <input
                  value={newApiKeyDescription}
                  onChange={(e) => setNewApiKeyDescription(e.target.value)}
                  placeholder="备注，例如 main key"
                />
                <button type="submit">
                  <Plus size={18} /> 添加 Key
                </button>
                {apiKeyMessage && <div className="settings-message">{apiKeyMessage}</div>}
              </form>

              <div className="settings-panel">
                <h3>已配置 API Key</h3>
                {apiKeys.length === 0 ? (
                  <p className="muted">还没有添加 API Key。</p>
                ) : (
                  <div className="api-key-list">
                    {apiKeys.map((key) => (
                      <div className="api-key-row" key={key.id}>
                        <div>
                          <strong>{key.description || 'Dwellir API Key'}</strong>
                          <span>{key.key_value.slice(0, 8)}...{key.key_value.slice(-4)}</span>
                        </div>
                        <button type="button" onClick={() => handleDeleteApiKey(key.id)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
           </div>
        )}
      </div>
    </div>
  );
}

export default App;
