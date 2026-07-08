import React, { useState, useEffect } from 'react';
import { Key, Activity, Users, Eye, EyeOff, MoreVertical, UserPlus, Database, Clock, Download, Save, RefreshCw, X, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import api from '../api/client';

export default function Settings() {
  const [showApiModal, setShowApiModal] = useState(false);
  const [credentials, setCredentials] = useState({
    deepseek: '',
    nano_banana: '',
    serper: '',
    openrouter: ''
  });
  const [verifyStatus, setVerifyStatus] = useState({});
  const [verifying, setVerifying] = useState({});

  useEffect(() => {
    if (showApiModal) {
      fetchCredentials();
    }
  }, [showApiModal]);

  const fetchCredentials = async () => {
    try {
      const res = await api.get('/settings/credentials');
      setCredentials(res.data);
    } catch (err) {
      console.error("Failed to fetch credentials", err);
    }
  };

  const handleVerify = async (toolKey) => {
    setVerifying(prev => ({ ...prev, [toolKey]: true }));
    try {
      const res = await api.post(`/settings/verify/${toolKey}`);
      setVerifyStatus(prev => ({ 
        ...prev, 
        [toolKey]: { status: res.data.status, message: res.data.message || res.data.data?.label, credits: res.data.credits_remaining } 
      }));
    } catch (err) {
      setVerifyStatus(prev => ({ 
        ...prev, 
        [toolKey]: { status: 'error', message: err.response?.data?.message || 'Verification failed' } 
      }));
    } finally {
      setVerifying(prev => ({ ...prev, [toolKey]: false }));
    }
  };

  const renderVerifyResult = (toolKey) => {
    const status = verifyStatus[toolKey];
    if (!status) return null;
    if (status.status === 'success') {
      return (
        <div className="flex flex-col mt-2">
          <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
            <CheckCircle2 size={14} /> {status.message}
          </div>
          {status.credits !== undefined && (
            <div className="text-xs text-slate-500 mt-1">Remaining Credits: <span className="font-bold text-slate-700">{status.credits}</span></div>
          )}
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 text-xs text-rose-500 font-semibold mt-2">
        <XCircle size={14} /> {status.message}
      </div>
    );
  };

  return (
    <div className="h-full bg-slate-50 flex flex-col p-6 overflow-auto text-slate-800 font-sans">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800 tracking-tight">System Configuration</h1>
        <div className="flex gap-3">
          <button className="px-3 py-1.5 border border-slate-300 rounded-md text-sm font-semibold text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition-colors">Export Logs</button>
          <button className="px-3 py-1.5 bg-[#3626A7] text-white rounded-md text-sm font-semibold hover:bg-blue-800 shadow-sm transition-colors">Save All Changes</button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <div className="xl:col-span-2 flex flex-col gap-3">
          <div className="flex items-center gap-2 text-[15px] font-bold text-slate-800 mb-1">
             <Key size={16} className="text-blue-600" /> API Connections
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-800 text-[15px]">AI Tools Credentials</h3>
              <p className="text-sm text-slate-500 mt-1">Manage API keys for Deepseek, Nano Banana, Gemini (OpenRouter), and Serper API.</p>
            </div>
            <button 
              onClick={() => setShowApiModal(true)}
              className="px-4 py-2 bg-indigo-50 text-indigo-700 font-semibold rounded-md border border-indigo-200 hover:bg-indigo-100 transition-colors text-sm"
            >
              Manage Credentials
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-[15px] font-bold text-slate-800 mb-1">
             <Activity size={16} className="text-blue-600" /> System Health
          </div>
          <div className="flex flex-col gap-3">
            {/* Redis Server */}
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                 <div className="w-9 h-9 rounded-full bg-rose-50 flex items-center justify-center text-rose-500">
                   <Database size={16} />
                 </div>
                 <div>
                   <div className="font-semibold text-slate-800 text-sm">Redis Server</div>
                   <div className="text-[11px] text-slate-500">6379 / main-cache</div>
                 </div>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-500 tracking-wide">
                <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div> UP
              </div>
            </div>

            {/* Celery Beat */}
            <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                 <div className="w-9 h-9 rounded-full bg-orange-50 flex items-center justify-center text-orange-500">
                   <Clock size={16} />
                 </div>
                 <div>
                   <div className="font-semibold text-slate-800 text-sm">Celery Beat</div>
                   <div className="text-[11px] text-slate-500">Scheduler engine</div>
                 </div>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-500 tracking-wide">
                <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div> POLLING
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 flex-1">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2 text-[15px] font-bold text-slate-800">
            <Users size={16} className="text-blue-600" /> User Permissions &amp; Access
          </div>
          <button className="flex items-center gap-1.5 px-3 py-1.5 border border-[#3626A7] text-[#3626A7] rounded-md text-xs font-bold hover:bg-[#3626A7] hover:text-white transition-colors">
            <UserPlus size={14} /> Invite User
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl shadow-[0_2px_10px_-3px_rgba(6,81,237,0.1)] overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-[#f8f9fa] border-b border-slate-200">
              <tr>
                <th className="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-1/3">User Identifier</th>
                <th className="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-1/6">Role</th>
                <th className="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider flex-1">Access Level</th>
                <th className="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-[80px] text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr className="hover:bg-slate-50/60 transition-colors">
                <td className="px-5 py-3 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#eef0ff] flex items-center justify-center text-[#3626A7] font-bold text-xs border border-[#e2e8f0]">SC</div>
                  <div>
                    <div className="font-bold text-slate-800 text-[13px]">Sarah Chen</div>
                    <div className="text-[11px] text-slate-500">s.chen@pipeline.io</div>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <span className="bg-[#3626A7] text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shadow-sm">ADMIN</span>
                </td>
                <td className="px-5 py-3">
                  <div className="flex gap-1.5 flex-wrap">
                    <span className="bg-[#f1f5f9] border border-slate-200 text-slate-600 text-[9px] font-bold px-1.5 py-0.5 rounded">Full Control</span>
                    <span className="bg-[#f1f5f9] border border-slate-200 text-slate-600 text-[9px] font-bold px-1.5 py-0.5 rounded">Billing</span>
                    <span className="bg-[#f1f5f9] border border-slate-200 text-slate-600 text-[9px] font-bold px-1.5 py-0.5 rounded">Infrastructure</span>
                  </div>
                </td>
                <td className="px-5 py-3 text-right">
                  <button className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100"><MoreVertical size={16} /></button>
                </td>
              </tr>
              <tr className="hover:bg-slate-50/60 transition-colors">
                <td className="px-5 py-3 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#f1f5f9] flex items-center justify-center text-slate-600 font-bold text-xs border border-slate-200">MW</div>
                  <div>
                    <div className="font-bold text-slate-800 text-[13px]">Marcus Wright</div>
                    <div className="text-[11px] text-slate-500">m.wright@external.com</div>
                  </div>
                </td>
                <td className="px-5 py-3">
                  <span className="bg-white border border-slate-300 text-slate-600 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shadow-sm">NORMAL</span>
                </td>
                <td className="px-5 py-3">
                  <div className="flex gap-1.5 flex-wrap">
                    <span className="bg-[#f1f5f9] border border-slate-200 text-slate-600 text-[9px] font-bold px-1.5 py-0.5 rounded">Create Job</span>
                    <span className="bg-[#f1f5f9] border border-slate-200 text-slate-600 text-[9px] font-bold px-1.5 py-0.5 rounded">Downloads</span>
                    <span className="bg-indigo-50 border border-indigo-100 text-indigo-600 italic text-[9px] font-bold px-1.5 py-0.5 rounded">RESTRICTED</span>
                  </div>
                </td>
                <td className="px-5 py-3 text-right">
                  <button className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100"><MoreVertical size={16} /></button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Floating Refresh Button */}
      <button className="absolute bottom-6 right-6 bg-[#3626A7] hover:bg-blue-800 text-white rounded-lg shadow-xl px-4 py-2.5 flex items-center gap-2 font-bold text-sm transition-all transform hover:scale-105 border border-indigo-700">
        <RefreshCw size={14} /> Refresh
      </button>

      {/* AI Credentials Modal */}
      {showApiModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <Key size={18} className="text-blue-600" /> AI Tools Credentials
              </h2>
              <button onClick={() => setShowApiModal(false)} className="text-slate-400 hover:text-slate-700">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50/50">
              {/* Deepseek */}
              <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-semibold text-slate-800 text-[14px]">Deepseek (LLM)</h3>
                  <span className="bg-indigo-50 text-indigo-600 text-[9px] font-bold px-2 py-0.5 rounded border border-indigo-100 uppercase">ACTIVE</span>
                </div>
                <div className="relative mb-3">
                  <input type="password" value={credentials.deepseek || "••••••••••••••••"} className="w-full bg-slate-50 border border-slate-200 rounded-md p-2 text-xs text-slate-600 font-mono tracking-widest" readOnly />
                </div>
                <button 
                  onClick={() => handleVerify('deepseek')}
                  disabled={verifying.deepseek}
                  className="w-full py-1.5 border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50 flex justify-center items-center gap-2"
                >
                  {verifying.deepseek ? <Loader2 size={14} className="animate-spin" /> : "Verify Connection"}
                </button>
                {renderVerifyResult('deepseek')}
              </div>
              
              {/* Nano Banana (via OpenRouter) */}
              <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-semibold text-slate-800 text-[14px]">Nano Banana (via OpenRouter)</h3>
                  <span className="bg-emerald-50 text-emerald-600 text-[9px] font-bold px-2 py-0.5 rounded border border-emerald-100 uppercase">ACTIVE</span>
                </div>
                <div className="relative mb-3">
                  <input type="password" value={credentials.openrouter || "••••••••••••••••"} className="w-full bg-slate-50 border border-slate-200 rounded-md p-2 text-xs text-slate-600 font-mono tracking-widest" readOnly />
                </div>
                <button 
                  onClick={() => handleVerify('openrouter')}
                  disabled={verifying.openrouter}
                  className="w-full py-1.5 border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50 flex justify-center items-center gap-2"
                >
                  {verifying.openrouter ? <Loader2 size={14} className="animate-spin" /> : "Verify & Check Credits"}
                </button>
                {renderVerifyResult('openrouter')}
              </div>

              
              {/* Serper API */}
              <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-semibold text-slate-800 text-[14px]">Serper API</h3>
                  <span className="bg-slate-100 text-slate-500 text-[9px] font-bold px-2 py-0.5 rounded border border-slate-200 uppercase">PROXY</span>
                </div>
                <div className="relative mb-3">
                  <input type="password" value={credentials.serper || "••••••••••••••••"} className="w-full bg-slate-50 border border-slate-200 rounded-md p-2 text-xs text-slate-600 font-mono tracking-widest" readOnly />
                </div>
                <button 
                  onClick={() => handleVerify('serper')}
                  disabled={verifying.serper}
                  className="w-full py-1.5 border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50 flex justify-center items-center gap-2"
                >
                  {verifying.serper ? <Loader2 size={14} className="animate-spin" /> : "Verify Connection"}
                </button>
                {renderVerifyResult('serper')}
              </div>
            </div>
            
            <div className="px-6 py-4 border-t border-slate-100 bg-white flex justify-end">
              <button 
                onClick={() => setShowApiModal(false)}
                className="px-5 py-2 bg-[#3626A7] text-white rounded-md text-sm font-semibold hover:bg-blue-800 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
