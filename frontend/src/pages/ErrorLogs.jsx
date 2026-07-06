import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { AlertTriangle, Clock, ServerCrash, XCircle, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';

export default function ErrorLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/dashboard/error-logs?limit=100');
      setLogs(res.data.items || []);
      setError('');
    } catch (err) {
      console.error('Failed to fetch error logs:', err);
      setError('Failed to load error logs. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  if (loading && logs.length === 0) {
    return (
      <div className="flex justify-center items-center h-[calc(100vh-6rem)]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Error Logs</h1>
          <p className="text-sm text-slate-500 mt-1">Review recently failed or aborted pipeline tasks.</p>
        </div>
        <button 
          onClick={fetchLogs}
          className="text-sm font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 px-4 py-2 rounded-md shadow-sm transition-colors"
        >
          Refresh Logs
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-start gap-3 border border-red-100">
          <ServerCrash size={20} className="shrink-0 mt-0.5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {logs.length === 0 && !loading && !error ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 flex flex-col items-center justify-center text-center shadow-sm">
          <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mb-4">
            <CheckCircle2 className="text-emerald-500" size={32} />
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-1">No Errors Found!</h3>
          <p className="text-slate-500 text-sm max-w-md">Your pipeline is running smoothly. There are no recent failed or aborted tasks.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="divide-y divide-slate-100">
            {logs.map((log) => (
              <div key={log.job_id} className="p-5 hover:bg-slate-50/50 transition-colors">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-3">
                    {log.status === 'failed' ? (
                      <div className="p-2 bg-red-50 text-red-600 rounded-lg shrink-0">
                        <XCircle size={18} />
                      </div>
                    ) : (
                      <div className="p-2 bg-amber-50 text-amber-600 rounded-lg shrink-0">
                        <AlertTriangle size={18} />
                      </div>
                    )}
                    <div>
                      <h3 className="font-bold text-slate-800 text-base">{log.task_name}</h3>
                      <a href={log.source_url} target="_blank" rel="noopener noreferrer" className="text-sm text-slate-500 hover:text-blue-600 transition-colors truncate block max-w-lg mt-0.5">
                        {log.source_url}
                      </a>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <span className={clsx(
                      "px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider",
                      log.status === 'failed' ? "bg-red-50 text-red-700 border border-red-100" : "bg-amber-50 text-amber-700 border border-amber-100"
                    )}>
                      {log.status}
                    </span>
                    <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                      <Clock size={12} />
                      {new Date(log.created_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
                    </div>
                  </div>
                </div>
                
                <div className={clsx(
                  "p-4 rounded-lg border text-sm font-mono overflow-x-auto",
                  log.status === 'failed' ? "bg-red-50/30 border-red-100 text-red-800" : "bg-amber-50/30 border-amber-100 text-amber-800"
                )}>
                  <div className="font-sans font-bold mb-1 text-xs opacity-70 uppercase tracking-wider">
                    {log.status === 'failed' ? 'Error Details' : 'Abort Reason'}
                  </div>
                  {log.error_message || "No error message provided."}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
