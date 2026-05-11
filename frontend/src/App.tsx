import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LayoutDashboard, Flame, Settings, FileText, LogOut, Plus, Trash2, RefreshCw } from 'lucide-react';
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

interface SystemLog {
  id: number;
  timestamp: string;
  level: string;
  message: string;
  module: string;
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
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [syncing, setSyncing] = useState(false);

  const authHeaders = (authToken = token) => ({ 'X-Admin-Token': authToken });

  useEffect(() => {
    if (!token) return;

    fetchData(token);
    fetchApiKeys(token);
    fetchLogs(token);
    const interval = setInterval(() => fetchData(token), 10000);
    return () => clearInterval(interval);
  }, [token]);

  const fetchData = async (authToken: string) => {
    try {
      const res = await axios.get('/api/subnets', {
        headers: authHeaders(authToken),
      });
      setSubnets(res.data.filter((subnet: Subnet) => subnet.netuid !== 0));
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
      handleSync();
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

  const fetchLogs = async (authToken = token) => {
    if (!authToken) return;

    try {
      const res = await axios.get('/api/logs', {
        headers: authHeaders(authToken),
      });
      setLogs(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await axios.post('/api/sync', {}, { headers: authHeaders() });
      await fetchData(token);
      await fetchLogs(token);
      setApiKeyMessage('已触发同步，请查看看板和运行日志。');
    } catch (err) {
      setApiKeyMessage('同步失败，请查看运行日志。');
      await fetchLogs(token);
    } finally {
      setSyncing(false);
    }
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
  const nonImmuneSubnets = subnets.filter((s) => !s.is_immune).sort((a, b) => a.ema - b.ema);
  const immuneSubnets = subnets.filter((s) => s.is_immune);
  const evictionCandidate = nonImmuneSubnets[0];

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
              <button onClick={handleSync} disabled={syncing}>
                <RefreshCw size={18} /> {syncing ? '同步中' : '立即同步'}
              </button>
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

        {activeTab === 'racing' && (
          <div className="racing-page">
            <div className="page-header">
              <h2>赛马机制</h2>
              <button onClick={handleSync} disabled={syncing}>
                <RefreshCw size={18} /> {syncing ? '同步中' : '立即同步'}
              </button>
            </div>

            {subnets.length === 0 ? (
              <div className="empty-state">
                <h3>暂无赛马数据</h3>
                <p>请先在系统设置添加 Dwellir API Key，然后点击立即同步。</p>
                <button onClick={() => setActiveTab('settings')}>去系统设置</button>
              </div>
            ) : (
              <>
                <div className="metric-grid">
                  <div className="metric-card">
                    <span>当前子网</span>
                    <strong>{subnets.length}</strong>
                  </div>
                  <div className="metric-card">
                    <span>最大容量</span>
                    <strong>128</strong>
                  </div>
                  <div className="metric-card">
                    <span>非免疫期</span>
                    <strong>{nonImmuneSubnets.length}</strong>
                  </div>
                  <div className="metric-card">
                    <span>免疫期</span>
                    <strong>{immuneSubnets.length}</strong>
                  </div>
                </div>

                {evictionCandidate && (
                  <div className="risk-panel">
                    <h3>当前最低 EMA</h3>
                    <div className="risk-subnet">
                      <strong>{evictionCandidate.name} (SN{evictionCandidate.netuid})</strong>
                      <span>EMA: {evictionCandidate.ema.toFixed(4)}</span>
                      <span>Alpha 价格: τ{evictionCandidate.alpha_price.toFixed(4)}</span>
                    </div>
                  </div>
                )}

                <div className="settings-panel">
                  <h3>非免疫期子网，按 EMA 从低到高</h3>
                  <div className="racing-list">
                    {nonImmuneSubnets.slice(0, 30).map((subnet, index) => (
                      <div className="racing-row" key={subnet.netuid}>
                        <span>#{index + 1}</span>
                        <strong>{subnet.name} (SN{subnet.netuid})</strong>
                        <em>EMA {subnet.ema.toFixed(4)}</em>
                        <em>τ{subnet.alpha_price.toFixed(4)}</em>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
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
                <button type="button" onClick={handleSync} disabled={syncing}>
                  <RefreshCw size={18} /> {syncing ? '同步中' : '立即同步'}
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

        {activeTab === 'logs' && (
          <div className="logs-page">
            <div className="page-header">
              <h2>运行日志</h2>
              <button onClick={() => fetchLogs()}>
                <RefreshCw size={18} /> 刷新
              </button>
            </div>
            {logs.length === 0 ? (
              <div className="empty-state">
                <h3>暂无日志</h3>
                <p>点击“立即同步”后，如果后端遇到 API、网络或解析问题，会在这里显示。</p>
              </div>
            ) : (
              <div className="log-list">
                {logs.map((log) => (
                  <div className={`log-row level-${log.level.toLowerCase()}`} key={log.id}>
                    <span>{new Date(log.timestamp).toLocaleString()}</span>
                    <strong>{log.level}</strong>
                    <em>{log.module}</em>
                    <p>{log.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
