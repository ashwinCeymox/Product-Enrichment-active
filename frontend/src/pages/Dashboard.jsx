import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { Layers, Clock, CheckCircle, XCircle, AlertCircle, RefreshCcw } from 'lucide-react';
import clsx from 'clsx';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showAllTasks, setShowAllTasks] = useState(false);

  const fetchDashboardData = async () => {
    setIsRefreshing(true);
    try {
      const [statsRes, activityRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/dashboard/recent-activity?limit=50')
      ]);
      setStats(statsRes.data);
      setActivity(activityRes.data.items || []);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success': return <CheckCircle size={16} className="text-emerald-500" />;
      case 'failed': return <XCircle size={16} className="text-red-500" />;
      default: return <Clock size={16} className="text-blue-500" />;
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex justify-center items-center h-[calc(100vh-6rem)]">
        <RefreshCcw className="animate-spin text-slate-400" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute right-0 top-0 w-16 h-16 bg-blue-50 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-4 relative z-10">
            <h3 className="text-xs font-bold text-slate-500 tracking-wider uppercase">Total Jobs</h3>
            <Layers size={18} className="text-blue-500" />
          </div>
          <p className="text-4xl font-bold text-slate-800 relative z-10">{stats?.total_jobs || 0}</p>
        </div>
        
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute right-0 top-0 w-16 h-16 bg-amber-50 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-4 relative z-10">
            <h3 className="text-xs font-bold text-slate-500 tracking-wider uppercase">Pending Approvals</h3>
            <Clock size={18} className="text-amber-500" />
          </div>
          <p className="text-4xl font-bold text-slate-800 relative z-10">{stats?.pending_approvals || 0}</p>
          {stats?.approval_breakdown && (
            <div className="flex items-center gap-3 mt-3 text-[11px] font-semibold text-slate-500 relative z-10">
              <span className="bg-slate-100 px-2 py-0.5 rounded-full" title="JSON">{stats.approval_breakdown.json_count} JSON</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded-full" title="Images">{stats.approval_breakdown.image_count} IMG</span>
              <span className="bg-slate-100 px-2 py-0.5 rounded-full" title="HTML">{stats.approval_breakdown.html_count} HTML</span>
            </div>
          )}
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute right-0 top-0 w-16 h-16 bg-emerald-50 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-4 relative z-10">
            <h3 className="text-xs font-bold text-slate-500 tracking-wider uppercase">Completed</h3>
            <CheckCircle size={18} className="text-emerald-500" />
          </div>
          <p className="text-4xl font-bold text-slate-800 relative z-10">{stats?.completed || 0}</p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between relative overflow-hidden group">
          <div className="absolute right-0 top-0 w-16 h-16 bg-rose-50 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-4 relative z-10">
            <h3 className="text-xs font-bold text-slate-500 tracking-wider uppercase">Failed</h3>
            <XCircle size={18} className="text-rose-500" />
          </div>
          <p className="text-4xl font-bold text-slate-800 relative z-10">{stats?.failed || 0}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
          <h2 className="text-lg font-bold text-slate-800">Task Queue Preview</h2>
          <button onClick={fetchDashboardData} className="text-slate-400 hover:text-slate-600 transition-colors p-1" title="Refresh">
            <RefreshCcw size={16} className={isRefreshing ? "animate-spin text-blue-500" : ""} />
          </button>
        </div>
        
        {activity.length === 0 ? (
          <div className="text-center text-slate-500 py-16 flex flex-col items-center bg-white">
            <AlertCircle size={48} className="text-slate-200 mb-4" />
            <p className="font-medium text-slate-400">No recent activity found.</p>
          </div>
        ) : (
          <div className="bg-white">
            <div className={clsx("divide-y divide-slate-100", showAllTasks ? "max-h-[60vh] overflow-y-auto" : "")}>
              {(showAllTasks ? activity : activity.slice(0, 5)).map((item, idx) => (
                <div key={item.job_id || idx} className="p-5 hover:bg-slate-50/80 transition-colors flex items-center justify-between">
                  <div className="flex flex-col gap-1.5 max-w-[65%]">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-slate-800 text-sm">{item.task_name}</span>
                      <span className="text-[11px] font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{new Date(item.created_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}</span>
                    </div>
                    <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-slate-500 hover:text-blue-600 truncate transition-colors">
                      {item.source_url}
                    </a>
                  </div>
                  
                  <div className="flex flex-col items-end gap-2.5 min-w-[140px]">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(item.status)}
                      <span className="text-[13px] font-bold text-slate-700 uppercase tracking-wide">
                        {item.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    
                    {item.status !== 'success' && item.status !== 'failed' && (
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200">
                        <div 
                          className="bg-blue-500 h-full transition-all duration-1000 ease-out" 
                          style={{ width: `${item.progress || 0}%` }} 
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            {activity.length > 5 && !showAllTasks && (
              <div className="p-3 border-t border-slate-100 flex justify-center bg-slate-50">
                <button 
                  onClick={() => setShowAllTasks(true)}
                  className="text-[13px] font-bold text-blue-600 hover:text-blue-800 transition-colors py-2 px-6 rounded-lg hover:bg-blue-50"
                >
                  View More ({activity.length - 5} additional tasks)
                </button>
              </div>
            )}
            {showAllTasks && (
              <div className="p-3 border-t border-slate-100 flex justify-center bg-slate-50 shadow-[0_-10px_15px_-3px_rgba(0,0,0,0.05)] relative z-10">
                <button 
                  onClick={() => setShowAllTasks(false)}
                  className="text-[13px] font-bold text-slate-500 hover:text-slate-700 transition-colors py-2 px-6 rounded-lg hover:bg-slate-200"
                >
                  View Less
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
