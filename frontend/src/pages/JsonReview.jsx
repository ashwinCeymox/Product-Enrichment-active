import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { 
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Check, X, FileJson, Loader2, RefreshCw } from 'lucide-react';
import clsx from 'clsx';

export default function JsonReview() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jsonData, setJsonData] = useState('');
  const [activeTab, setActiveTab] = useState('table');
  const [saving, setSaving] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await api.get('/jobs/?status=waiting_for_approval');
      setData(res.data.jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleReview = (job) => {
    setSelectedJob(job);
    setJsonData(JSON.stringify(job.product_data || {}, null, 2));
  };

  const handleApprove = async () => {
    if (!selectedJob) return;
    setSaving(true);
    try {
      let parsedData = {};
      try { parsedData = JSON.parse(jsonData); } catch(e) { alert('Invalid JSON format!'); setSaving(false); return; }
      
      await api.post(`/jobs/${selectedJob.id}/approve`, { product_data: parsedData });
      setSelectedJob(null);
      fetchJobs();
    } catch (err) {
      console.error(err);
      alert('Failed to approve job');
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!selectedJob) return;
    setSaving(true);
    try {
      await api.post(`/jobs/${selectedJob.id}/reject`);
      setSelectedJob(null);
      fetchJobs();
    } catch (err) {
      console.error(err);
      alert('Failed to reject job');
    } finally {
      setSaving(false);
    }
  };

  const columnHelper = createColumnHelper();
  const columns = [
    columnHelper.accessor('task_name', { header: 'Task Name' }),
    columnHelper.accessor('url', { 
      header: 'Source URL',
      cell: info => <div className="max-w-xs truncate" title={info.getValue()}>{info.getValue()}</div> 
    }),
    columnHelper.accessor('created_at', { 
      header: 'Date',
      cell: info => new Date(info.getValue()).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
    }),
    columnHelper.display({
      id: 'actions',
      header: 'Actions',
      cell: (info) => (
        <button 
          onClick={() => handleReview(info.row.original)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-md text-sm font-medium hover:bg-indigo-100 transition-colors"
        >
          <FileJson size={16} /> Review JSON
        </button>
      )
    })
  ];

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-800">JSON Approval Queue</h2>
          <p className="text-sm text-slate-500 mt-1">Review, edit, and approve extracted product attributes before image generation.</p>
        </div>
        <button 
          onClick={fetchJobs} 
          className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 rounded-md shadow-sm text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={16} className={clsx(loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm text-left">
            <thead className="bg-slate-50">
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map(header => (
                    <th key={header.id} className="px-6 py-3 font-semibold text-slate-700">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {loading && data.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-slate-500">
                    <Loader2 className="animate-spin mx-auto mb-2 text-slate-400" size={24} />
                    Loading queue...
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-slate-500">
                    No items awaiting approval.
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map(row => (
                  <tr key={row.id} className="hover:bg-slate-50">
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-6 py-4 whitespace-nowrap text-slate-600">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Editor Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl flex flex-col max-h-full overflow-hidden">
            <div className="px-6 pt-4 border-b border-slate-200 bg-slate-50">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-800">Review Extraction Data</h3>
                  <p className="text-sm text-slate-500 max-w-lg truncate">{selectedJob.task_name} — {selectedJob.url}</p>
                </div>
                <button 
                  onClick={() => setSelectedJob(null)} 
                  className="text-slate-400 hover:text-slate-600 p-1"
                  disabled={saving}
                >
                  <X size={20} />
                </button>
              </div>
              <div className="flex gap-4 border-b border-slate-200">
                <button
                  className={clsx("pb-2 px-1 text-sm font-medium border-b-2 transition-colors", activeTab === 'table' ? "border-primary text-primary" : "border-transparent text-slate-500 hover:text-slate-700")}
                  onClick={() => setActiveTab('table')}
                >
                  Table View
                </button>
                <button
                  className={clsx("pb-2 px-1 text-sm font-medium border-b-2 transition-colors", activeTab === 'json' ? "border-primary text-primary" : "border-transparent text-slate-500 hover:text-slate-700")}
                  onClick={() => setActiveTab('json')}
                >
                  Raw JSON
                </button>
              </div>
            </div>
            
            <div className="flex-1 p-6 overflow-y-auto bg-slate-100">
              {activeTab === 'json' ? (
                <textarea 
                  className="w-full min-h-[500px] h-[65vh] font-mono text-sm p-4 rounded-md border border-slate-300 focus:ring-primary focus:border-primary shadow-inner bg-white overflow-auto"
                  value={jsonData}
                  onChange={e => setJsonData(e.target.value)}
                  spellCheck={false}
                  wrap="off"
                />
              ) : (
                <div className="bg-white rounded-md border border-slate-300 shadow-inner min-h-[500px] h-[65vh] overflow-auto">
                  {(() => {
                    let parsed = {};
                    let isValid = true;
                    try {
                      parsed = JSON.parse(jsonData);
                      if (typeof parsed !== 'object' || parsed === null) throw new Error();
                    } catch (e) {
                      isValid = false;
                    }

                    if (!isValid) {
                      return (
                        <div className="flex items-center justify-center h-full text-red-500 text-sm">
                          Invalid JSON format. Please fix in the Raw JSON tab first.
                        </div>
                      );
                    }
                    
                    const keys = Object.keys(parsed);
                    if (keys.length === 0) {
                      return (
                        <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm">
                          <p>The JSON object is empty.</p>
                          <button onClick={() => setActiveTab('json')} className="mt-2 text-primary hover:underline">Switch to Raw JSON to add data manually</button>
                        </div>
                      );
                    }

                    return (
                      <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50 sticky top-0">
                          <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider w-1/3">Key</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider w-2/3">Value</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200">
                          {keys.map(key => {
                            const val = parsed[key];
                            const isStringOrNumber = typeof val === 'string' || typeof val === 'number';
                            return (
                              <tr key={key} className="hover:bg-slate-50">
                                <td className="px-4 py-3 text-sm font-medium text-slate-700 align-top">
                                  {key}
                                </td>
                                <td className="px-4 py-3 align-top">
                                  {isStringOrNumber ? (
                                    <textarea 
                                      value={val}
                                      rows={String(val).length > 60 ? 3 : 1}
                                      onChange={(e) => {
                                        const newParsed = { ...parsed, [key]: e.target.value };
                                        setJsonData(JSON.stringify(newParsed, null, 2));
                                      }}
                                      className="w-full text-sm border-slate-300 rounded-md shadow-sm focus:border-primary focus:ring-primary p-1.5 border bg-white overflow-auto"
                                    />
                                  ) : (
                                    <div className="text-sm text-slate-500 italic bg-slate-100 p-1.5 rounded border border-slate-200">
                                      {JSON.stringify(val)}
                                      <span className="block text-xs mt-1 text-slate-400">(Nested object/array - edit in Raw JSON tab)</span>
                                    </div>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    );
                  })()}
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
              <button 
                onClick={handleReject}
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 border border-red-300 text-red-700 bg-white rounded-md font-medium text-sm hover:bg-red-50 focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
              >
                <X size={16} /> Reject
              </button>
              <button 
                onClick={handleApprove}
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-md font-medium text-sm hover:bg-emerald-700 focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50"
              >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                Approve & Continue
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
