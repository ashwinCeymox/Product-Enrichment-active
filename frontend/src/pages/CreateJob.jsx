import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { UploadCloud, Play, Calendar, AlertCircle, Loader2, Clock, CheckCircle2, XCircle, X } from 'lucide-react';
import clsx from 'clsx';

export default function CreateJob() {
  const [taskName, setTaskName] = useState('');
  const [urls, setUrls] = useState('');
  const [priority, setPriority] = useState('low');
  const [scheduledDate, setScheduledDate] = useState('');
  const [productType, setProductType] = useState('simple');
  
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  
  // Queue state
  const [queue, setQueue] = useState([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [showAllQueue, setShowAllQueue] = useState(false);
  const [hiddenJobs, setHiddenJobs] = useState(new Set());
  
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [taskToDelete, setTaskToDelete] = useState(null);

  const urlList = urls.split('\n').map(u => u.trim()).filter(Boolean);

  const fetchQueue = async () => {
    try {
      const res = await api.get('/dashboard/recent-activity?limit=50');
      setQueue(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch queue', err);
    } finally {
      setQueueLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!taskName || urlList.length === 0) return;
    
    setLoading(true);
    setMessage('');
    try {
      const res = await api.post('/jobs', {
        task_name: taskName,
        urls: urlList,
        priority: priority,
        scheduled_date: scheduledDate || null,
        product_type: productType,
        created_by: 'admin'
      });
      setMessage(`Success! ${res.data.message}`);
      setUrls('');
      setTaskName('');
      setScheduledDate('');
      setPriority('low');
      setProductType('simple');
      fetchQueue();
    } catch (err) {
      let errorMsg = err.message;
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map(d => `${d.loc?.[d.loc.length-1] || 'field'}: ${d.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      setMessage(`Error: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const confirmDeleteTask = (jobId, status) => {
    setTaskToDelete({ jobId, status });
    setShowDeleteModal(true);
  };

  const executeDeleteTask = async () => {
    if (!taskToDelete) return;
    const { jobId, status } = taskToDelete;
    try {
      await api.delete(`/jobs/${jobId}`);
      if (['success', 'failed', 'aborted'].includes(status)) {
        setHiddenJobs(prev => new Set([...prev, jobId]));
      }
      // Refresh the queue immediately after action
      setShowDeleteModal(false);
      setTaskToDelete(null);
      fetchQueue();
    } catch (err) {
      console.error('Failed to act on task', err);
    }
  };

  const filteredQueue = queue.filter(item => !hiddenJobs.has(item.job_id));

  const handleCsvUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setLoading(true);
    setMessage('');
    
    const formData = new FormData();
    formData.append('file', file);
    // Append query params since endpoint expects them as Query
    const queryParams = new URLSearchParams({
      task_name: taskName,
      url_column: 'url',
      priority: priority,
      product_type: productType,
      created_by: 'admin'
    });
    
    if (scheduledDate) {
      queryParams.append('scheduled_date', scheduledDate);
    }

    try {
      const res = await api.post(`/jobs/upload-csv?${queryParams.toString()}`, formData);
      setMessage(`Success! ${res.data.message}`);
      setUrls('');
      setTaskName('');
      setScheduledDate('');
      setPriority('low');
      setProductType('simple');
      fetchQueue();
    } catch (err) {
      let errorMsg = err.message;
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map(d => `${d.loc?.[d.loc.length-1] || 'field'}: ${d.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      setMessage(`Error: ${errorMsg}`);
    } finally {
      setLoading(false);
      e.target.value = ''; // Reset file input
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success': return <CheckCircle2 size={16} className="text-emerald-500" />;
      case 'failed': return <XCircle size={16} className="text-red-500" />;
      case 'pending':
      case 'queued':
      default:
        return <Clock size={16} className="text-blue-500" />;
    }
  };

  const formatTimeAgo = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Job Creation Form */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden flex flex-col h-full">
            <div className="p-4 border-b border-slate-200 bg-slate-50 shrink-0">
              <h2 className="text-lg font-semibold text-slate-800">Create Extraction Job</h2>
              <p className="text-sm text-slate-500 mt-1">Submit URLs to be scraped and processed by the AI pipeline.</p>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-6 flex-1">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Task Name</label>
                  <input 
                    type="text" 
                    required
                    value={taskName}
                    onChange={e => setTaskName(e.target.value)}
                    placeholder="e.g. JOOLA Spring Catalog"
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-primary focus:border-primary sm:text-sm"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Priority</label>
                  <select 
                    value={priority}
                    onChange={e => setPriority(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-primary focus:border-primary sm:text-sm bg-white"
                  >
                    <option value="low">Low</option>
                    <option value="normal">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Product Type</label>
                  <select 
                    value={productType}
                    onChange={e => setProductType(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-primary focus:border-primary sm:text-sm bg-white"
                  >
                    <option value="simple">Simple Product</option>
                    <option value="aplus">A+ Product</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Schedule Date <span className="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Calendar size={16} className="text-slate-400" />
                    </div>
                    <input 
                      type="date" 
                      value={scheduledDate}
                      onChange={e => setScheduledDate(e.target.value)}
                      className="w-full pl-10 px-3 py-2 border border-slate-300 rounded-md focus:ring-primary focus:border-primary sm:text-sm text-slate-700"
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">If left blank, task starts immediately.</p>
                </div>
              </div>

              <div>
                <div className="flex justify-between items-end mb-1">
                  <label className="block text-sm font-medium text-slate-700">Source URLs</label>
                  <span className="text-xs text-slate-500">{urlList.length} valid URL(s) detected</span>
                </div>
                <textarea 
                  required
                  rows={8}
                  value={urls}
                  onChange={e => setUrls(e.target.value)}
                  placeholder="https://example.com/product-1&#10;https://example.com/product-2"
                  className="w-full px-3 py-2 border border-slate-300 rounded-md font-mono text-sm focus:ring-primary focus:border-primary"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button 
                  type="submit" 
                  disabled={loading || !taskName || urlList.length === 0}
                  className="inline-flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-md font-medium text-sm hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 transition-colors"
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                  Start Processing
                </button>
                <div className="relative">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleCsvUpload}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    disabled={loading || !taskName}
                    title={!taskName ? "Please enter a Task Name first" : "Upload CSV"}
                  />
                  <button 
                    type="button"
                    disabled={loading || !taskName}
                    className="inline-flex items-center gap-2 bg-white text-slate-700 border border-slate-300 px-4 py-2 rounded-md font-medium text-sm hover:bg-slate-50 focus:outline-none transition-colors disabled:opacity-50"
                  >
                    <UploadCloud size={16} />
                    Upload CSV
                  </button>
                </div>
              </div>
              
              {message && (
                <div className={clsx("p-3 rounded-md text-sm", message.startsWith('Error') ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700")}>
                  {message}
                </div>
              )}
            </form>
          </div>
        </div>

        {/* Right Column: Task Queue Preview */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm flex flex-col sticky top-6" style={{ maxHeight: 'calc(100vh - 8rem)' }}>
            <div className="p-4 border-b border-slate-200 bg-slate-50 shrink-0">
              <h2 className="text-base font-semibold text-slate-800">Task Queue Preview</h2>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto">
              {queueLoading ? (
                <div className="flex justify-center items-center h-32">
                  <Loader2 className="animate-spin text-slate-400" size={24} />
                </div>
              ) : queue.length === 0 ? (
                <div className="text-center text-slate-500 py-8 text-sm flex flex-col items-center">
                  <AlertCircle size={32} className="text-slate-300 mb-3" />
                  <p>The queue is currently empty.</p>
                </div>
              ) : (
                <>
                  <ul className="space-y-3">
                    {(showAllQueue ? filteredQueue : filteredQueue.slice(0, 5)).map((item, idx) => (
                      <li key={item.job_id || idx} className="bg-slate-50 border border-slate-100 p-3 rounded-md shadow-sm text-sm relative group flex flex-col gap-2">
                        <button 
                          onClick={() => confirmDeleteTask(item.job_id, item.status)}
                          className="absolute top-2 right-2 p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors opacity-0 group-hover:opacity-100"
                          title={['success', 'failed', 'aborted'].includes(item.status) ? "Dismiss from view" : "Abort Task"}
                        >
                          <X size={14} />
                        </button>
                        <div className="flex justify-between items-start pr-6">
                          <span className="font-semibold text-slate-800 truncate pr-2">{item.task_name}</span>
                          <div className="flex items-center gap-2 shrink-0">
                            {item.created_at && (
                              <span className="text-[11px] font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded flex items-center gap-1" title={new Date(item.created_at).toLocaleString()}>
                                <Clock size={10} />
                                {formatTimeAgo(item.created_at)}
                              </span>
                            )}
                            {getStatusIcon(item.status)}
                          </div>
                        </div>
                        <div className="text-xs text-slate-500 truncate" title={item.source_url}>
                          {item.source_url}
                        </div>
                        <div className="flex justify-between items-center text-xs mt-1">
                          <span className="px-2 py-0.5 rounded-full bg-white border border-slate-200 font-medium text-slate-600 capitalize">
                            {item.status.replace('_', ' ')}
                          </span>
                          {item.progress > 0 && <span className="text-primary font-medium">{item.progress}%</span>}
                        </div>
                        
                        {(item.status === 'failed' || item.status === 'aborted') && item.error_message && (
                          <div className={clsx(
                            "mt-1 p-2 rounded border text-xs leading-relaxed",
                            item.status === 'failed' ? "bg-red-50/50 border-red-100 text-red-600" : "bg-amber-50/50 border-amber-100 text-amber-600"
                          )}>
                            <strong>{item.status === 'failed' ? 'Error: ' : 'Aborted: '}</strong>
                            {item.error_message}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                  {filteredQueue.length > 5 && !showAllQueue && (
                    <button 
                      onClick={() => setShowAllQueue(true)}
                      className="w-full mt-4 py-2 text-sm font-semibold text-primary hover:text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors"
                    >
                      View More ({filteredQueue.length - 5} Tasks)
                    </button>
                  )}
                  {showAllQueue && (
                    <button 
                      onClick={() => setShowAllQueue(false)}
                      className="w-full mt-4 py-2 text-sm font-semibold text-slate-500 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
                    >
                      View Less
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete Task Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex flex-col items-center justify-center backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex flex-col items-center text-center">
              <div className="w-12 h-12 bg-rose-100 text-rose-500 rounded-full flex items-center justify-center mb-4">
                <XCircle size={24} />
              </div>
              <h3 className="text-xl font-bold text-slate-800">
                {taskToDelete?.status === 'success' || taskToDelete?.status === 'failed' || taskToDelete?.status === 'aborted' 
                  ? 'Dismiss Task' 
                  : 'Abort Task'}
              </h3>
              <p className="text-sm text-slate-500 mt-2">
                {taskToDelete?.status === 'success' || taskToDelete?.status === 'failed' || taskToDelete?.status === 'aborted' 
                  ? 'Are you sure you want to dismiss this task from your view?' 
                  : 'Are you sure that you want to abort the task?'}
              </p>
            </div>
            
            <div className="p-4 bg-slate-50 flex justify-end gap-3">
              <button 
                onClick={() => { setShowDeleteModal(false); setTaskToDelete(null); }}
                className="px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-200 bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={executeDeleteTask}
                className="px-5 py-2.5 text-sm font-semibold text-white bg-rose-500 hover:bg-rose-600 rounded-lg shadow-sm transition-colors"
              >
                {taskToDelete?.status === 'success' || taskToDelete?.status === 'failed' || taskToDelete?.status === 'aborted' 
                  ? 'Dismiss' 
                  : 'Abort'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
