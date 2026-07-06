import React, { useState, useEffect } from 'react';
import { Image as ImageIcon, CheckCircle, RefreshCcw, Rocket, Layers, UploadCloud, Loader2, StopCircle, PlayCircle, Folder, FolderOpen, Maximize2, Minimize2, Trash2, ChevronLeft, ChevronRight, X, XCircle } from 'lucide-react';
import clsx from 'clsx';
import api from '../api/client';

export default function ImageQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeAssetGroup, setActiveAssetGroup] = useState(null);
  const [selectedVariationId, setSelectedVariationId] = useState(null);
  const [promptText, setPromptText] = useState("");
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hasInitialSelection, setHasInitialSelection] = useState(false);
  
  const [showStopModal, setShowStopModal] = useState(false);
  const [stopJobId, setStopJobId] = useState(null);
  
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [variationToDelete, setVariationToDelete] = useState(null);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 3000);
    return () => clearInterval(interval);
  }, []);

  // Handle default selection when queue loads or changes
  useEffect(() => {
    if (queue.length > 0 && !hasInitialSelection) {
      const firstJob = queue[0];
      setActiveJobId(firstJob.job_id);
      if (firstJob.assets && firstJob.assets.length > 0 && !activeAssetGroup) {
        setActiveAssetGroup(firstJob.assets[0].variation_group);
        setPromptText(firstJob.assets[0].prompt);
        setSelectedVariationId(null);
      }
      setHasInitialSelection(true);
    }
  }, [queue, hasInitialSelection, activeAssetGroup]);

  const fetchQueue = async () => {
    try {
      const res = await api.get('/images/queue');
      setQueue(res.data);
    } catch (err) {
      console.error('Failed to fetch image queue:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async (assetId) => {
    if (!assetId || !promptText) return;
    setIsRegenerating(true);
    try {
      await api.post(`/images/${assetId}/regenerate`, null, { params: { prompt_text: promptText } });
      await fetchQueue();
    } catch (err) {
      console.error('Failed to regenerate', err);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleApprove = async (assetId) => {
    if (!assetId) return;
    try {
      await api.post(`/images/${assetId}/approve`);
      await fetchQueue();
    } catch (err) {
      console.error('Failed to approve', err);
    }
  };

  const handleStop = async (jobId) => {
    if (!jobId) return;
    try {
      await api.post(`/images/job/${jobId}/stop`);
      setShowStopModal(false);
      await fetchQueue();
    } catch (err) {
      console.error('Failed to stop', err);
    }
  };

  const handleAbort = async (jobId) => {
    if (!jobId) return;
    try {
      await api.post(`/images/job/${jobId}/abort`);
      setShowStopModal(false);
      setActiveJobId(null);
      await fetchQueue();
    } catch (err) {
      console.error('Failed to abort', err);
    }
  };

  const handleRevert = async (jobId) => {
    if (!jobId) return;
    try {
      await api.post(`/images/job/${jobId}/revert`);
      setShowStopModal(false);
      setActiveJobId(null);
      await fetchQueue();
    } catch (err) {
      console.error('Failed to revert', err);
    }
  };

  const handleResume = async (jobId) => {
    if (!jobId) return;
    try {
      await api.post(`/images/job/${jobId}/resume`);
      await fetchQueue();
    } catch (err) {
      console.error('Failed to resume', err);
    }
  };

  const handleFinish = async (jobId) => {
    if (!jobId) return;
    try {
      await api.post(`/images/job/${jobId}/finish`);
      setActiveJobId(null);
      await fetchQueue();
      // Optional: redirect to bundle page
      // window.location.href = '/bundles';
    } catch (err) {
      console.error('Failed to finish', err);
    }
  };

  const confirmDeleteVariation = (e, assetId) => {
    e.stopPropagation();
    if (!assetId) return;
    setVariationToDelete(assetId);
    setShowDeleteModal(true);
  };

  const executeDeleteVariation = async () => {
    if (!variationToDelete) return;
    try {
      await api.delete(`/images/${variationToDelete}`);
      if (selectedVariationId === variationToDelete) {
        setSelectedVariationId(null);
      }
      setShowDeleteModal(false);
      setVariationToDelete(null);
      await fetchQueue();
    } catch (err) {
      console.error('Failed to delete variation', err);
    }
  };

  const activeJob = queue.find(j => j.job_id === activeJobId) || null;
  const activeAssets = activeJob ? activeJob.assets : [];
  
  const currentAssetIndex = activeAssets.findIndex(a => a.variation_group === activeAssetGroup);
  const currentAsset = activeAssets[currentAssetIndex] || activeAssets[0];
  const variations = currentAsset ? currentAsset.variations : [];
  
  const activeVariationId = selectedVariationId && variations.find(v => v.id === selectedVariationId) 
    ? selectedVariationId 
    : (variations.length > 0 ? variations[0].id : null);
    
  const activeVariation = variations.find(v => v.id === activeVariationId) || variations[0];
  const isGroupGenerating = variations.some(v => v.status === 'generating');

  const handlePrev = () => {
    if (currentAssetIndex > 0) {
      const nextAsset = activeAssets[currentAssetIndex - 1];
      setActiveAssetGroup(nextAsset.variation_group);
      setPromptText(nextAsset.prompt);
      setSelectedVariationId(null);
    }
  };

  const handleNext = () => {
    if (currentAssetIndex < activeAssets.length - 1) {
      const nextAsset = activeAssets[currentAssetIndex + 1];
      setActiveAssetGroup(nextAsset.variation_group);
      setPromptText(nextAsset.prompt);
      setSelectedVariationId(null);
    }
  };

  if (loading) {
    return (
      <div className="h-[calc(100vh-6rem)] flex items-center justify-center">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div className="h-[calc(100vh-6rem)] flex flex-col items-center justify-center text-slate-500">
        <ImageIcon size={48} className="text-slate-300 mb-4" />
        <h2 className="text-xl font-semibold mb-2">Image Review Empty</h2>
        <p>No jobs are currently waiting for image review or generation.</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-6rem)] flex gap-6 overflow-hidden">
      
      {/* LEFT PANEL: Project Assets */}
      <div className="w-1/4 min-w-[300px] flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50">
          <div className="text-xs font-bold text-slate-400 tracking-wider mb-1">PROJECT ASSETS</div>
          <h2 className="text-lg font-bold text-slate-800">Image Review</h2>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50">
          {queue.map(job => {
            const isJobActive = activeJobId === job.job_id;
            // Calculate percentage based on status or approved assets
            const totalAssets = job.assets.length;
            const approvedCount = job.assets.filter(a => a.variations.some(v => v.status === 'approved')).length;
            const percentage = job.status === 'image_generation_complete' ? 100 : (totalAssets > 0 ? Math.round((approvedCount / totalAssets) * 100) : 0);

            return (
              <div key={job.job_id} className="mb-2 bg-slate-50/30 rounded-xl overflow-hidden">
                <div 
                  className={clsx(
                    "flex justify-between items-center p-3 cursor-pointer transition-colors rounded-xl bg-slate-50/50",
                    isJobActive ? "border border-slate-100 shadow-sm" : "hover:bg-slate-100/50"
                  )}
                  onClick={() => {
                    if (isJobActive) {
                      setActiveJobId(null);
                    } else {
                      setActiveJobId(job.job_id);
                      if (job.assets.length > 0) {
                        setActiveAssetGroup(job.assets[0].variation_group);
                        setPromptText(job.assets[0].prompt);
                        setSelectedVariationId(null);
                      }
                    }
                  }}
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    {isJobActive ? <FolderOpen size={18} className="text-blue-600 flex-shrink-0" /> : <Folder size={18} className="text-blue-600 flex-shrink-0" />}
                    <span className="text-base font-bold text-slate-700 truncate">{job.task_name}</span>
                  </div>
                  <div className="flex-shrink-0 ml-2 relative w-10 h-10 flex items-center justify-center rounded-full border-2 border-slate-200 text-[11px] font-bold text-slate-700 bg-white shadow-sm">
                    {percentage}%
                  </div>
                </div>

                {isJobActive && (
                  <div className="p-3 pt-4 flex flex-col gap-3">
                    {job.assets.map(asset => {
                      const isApproved = asset.variations.some(v => v.status === 'approved');
                      const approvedVariation = asset.variations.find(v => v.status === 'approved');
                      const displayVariation = approvedVariation || asset.variations[0];
                      const isActive = activeAssetGroup === asset.variation_group;
                      return (
                        <div 
                          key={`${job.job_id}-${asset.variation_group}`}
                          onClick={() => {
                            setActiveAssetGroup(asset.variation_group);
                            setPromptText(asset.prompt);
                            setSelectedVariationId(null);
                          }}
                          className={clsx(
                            "p-3.5 rounded-xl border cursor-pointer transition-all relative overflow-hidden bg-white shadow-sm",
                            isActive 
                              ? "border-blue-500/50 shadow-md" 
                              : "border-slate-200 hover:border-slate-300 opacity-90"
                          )}
                        >
                          {isActive && (
                            <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-blue-600"></div>
                          )}
                          <div className="flex justify-between items-start mb-1">
                            <span className={clsx("text-sm font-bold tracking-wide truncate", isActive ? "text-slate-600" : "text-slate-500")}>
                              {asset.variation_group.toUpperCase()}
                            </span>
                            {isApproved && <CheckCircle size={14} className="text-emerald-500 flex-shrink-0 ml-2" />}
                          </div>
                          <div className="text-sm text-slate-400 truncate">{displayVariation?.asset_name || 'Generating...'}</div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {!activeJobId ? (
        <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col items-center justify-center text-slate-400">
          <Folder size={64} className="mb-6 text-slate-200" />
          <h2 className="text-xl font-bold text-slate-500 mb-2">No Task Selected</h2>
          <p className="text-sm text-slate-400">Click on a task in the left panel to review its generated assets.</p>
        </div>
      ) : (
        <>
          {/* MIDDLE PANEL: Active Image & Bottom Status */}
          <div className="flex-1 flex flex-col gap-6 overflow-hidden">
            
            {/* Top: Active Preview & Prompt Editor */}
            <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
            <h2 className="text-lg font-bold text-slate-800 uppercase tracking-wide">
              {currentAsset?.variation_group ? currentAsset.variation_group.replace('_', ' ') : 'Asset Preview'}
            </h2>
            <div className="flex items-center gap-3">
              {activeJob?.status === 'image_generation' && (
                <button 
                  onClick={() => { setStopJobId(activeJob.job_id); setShowStopModal(true); }}
                  className="flex items-center gap-1.5 text-xs font-bold text-rose-600 bg-rose-50 border border-rose-200 px-3 py-1.5 rounded-md shadow-sm hover:bg-rose-100 transition-colors"
                >
                  <StopCircle size={14} /> STOP
                </button>
              )}
              {(activeJob?.status === 'image_generation_complete' || activeJob?.status === 'image_generation_stopped') && (
                <button 
                  onClick={() => handleFinish(activeJob.job_id)}
                  className="flex items-center gap-1.5 text-xs font-bold text-blue-600 bg-blue-50 border border-blue-200 px-3 py-1.5 rounded-md shadow-sm hover:bg-blue-100 transition-colors"
                >
                  <CheckCircle size={14} /> APPROVE ALL
                </button>
              )}
              <div className="text-xs font-bold text-slate-500 bg-white border border-slate-200 px-3 py-1.5 rounded-md shadow-sm">
                {activeJob?.status === 'image_generation' ? 'GENERATING...' : activeJob?.status === 'image_generation_stopped' ? 'STOPPED' : 'COMPLETE'}
              </div>
            </div>
          </div>
          
          {/* Main Image Preview */}
          <div className="flex-1 bg-slate-100 p-6 flex flex-col relative overflow-hidden group">
            {variations.length > 0 && activeVariation ? (
              <>
                <div className="flex-1 flex items-center justify-center relative w-full h-full p-2">
                  <div 
                    className="relative w-full h-full flex items-center justify-center rounded-lg group/img cursor-zoom-in overflow-hidden shadow-inner bg-slate-200"
                    onClick={() => setIsFullscreen(true)}
                  >
                    {/* Blurred Background to fill space */}
                    <div 
                      className="absolute inset-0 bg-cover bg-center blur-3xl opacity-50 scale-110"
                      style={{ backgroundImage: `url(http://localhost:8000/${activeVariation.url})` }}
                    />
                    
                    {/* Actual Uncropped Image */}
                    <img 
                      src={`http://localhost:8000/${activeVariation.url}`} 
                      alt="Generated preview" 
                      className="relative z-0 max-h-full max-w-full rounded-lg object-contain shadow-2xl transition-transform duration-300 group-hover/img:scale-[1.02] bg-white"
                      onError={(e) => { e.target.onerror = null; e.target.src = activeVariation.url; }}
                    />
                    
                    {/* Dark overlay on hover with highly aesthetic VIEW button */}
                    <div className="absolute inset-0 z-10 bg-slate-900/10 opacity-0 group-hover/img:opacity-100 transition-opacity duration-300 flex items-center justify-center pointer-events-none rounded-lg">
                       <button className="bg-white/95 backdrop-blur-md text-slate-800 font-bold px-8 py-3.5 tracking-[0.2em] text-sm shadow-2xl rounded hover:bg-white hover:scale-105 transition-all pointer-events-auto flex items-center gap-2 border border-white/20">
                         <Maximize2 size={16} className="text-slate-500" />
                         VIEW
                       </button>
                    </div>

                    {/* Navigation Buttons (Centered vertically on edges) */}
                    <button 
                      onClick={(e) => { e.stopPropagation(); handlePrev(); }}
                      disabled={currentAssetIndex === 0}
                      className="absolute left-6 z-20 w-12 h-12 bg-white/90 backdrop-blur-sm hover:bg-white rounded-full flex items-center justify-center shadow-xl disabled:opacity-0 transition-all opacity-0 group-hover/img:opacity-100 border border-slate-100"
                    >
                      <ChevronLeft size={24} className="text-slate-800" />
                    </button>
                    
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleNext(); }}
                      disabled={currentAssetIndex === activeAssets.length - 1}
                      className="absolute right-6 z-20 w-12 h-12 bg-white/90 backdrop-blur-sm hover:bg-white rounded-full flex items-center justify-center shadow-xl disabled:opacity-0 transition-all opacity-0 group-hover/img:opacity-100 border border-slate-100"
                    >
                      <ChevronRight size={24} className="text-slate-800" />
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-full w-full text-slate-400 flex flex-col items-center justify-center">
                {activeJob?.status === 'image_generation_stopped' ? (
                  <StopCircle className="mb-2 text-rose-400" size={32} />
                ) : (
                  <Loader2 className="animate-spin mb-2" size={32} />
                )}
                <p>{activeJob?.status === 'image_generation_stopped' ? 'Generation Stopped.' : 'Generating Images via DeepSeek & Gemini Nano Banana...'}</p>
              </div>
            )}
          </div>

          {/* Prompt Editor */}
          <div className="border-t border-slate-200 bg-white p-5 flex flex-col shrink-0 @container">
            <div className="text-xs font-bold text-slate-400 tracking-wider mb-3">PROMPT EDITOR</div>
            <textarea 
              rows="5"
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              className="w-full bg-slate-900 text-slate-100 rounded-lg p-4 font-mono text-sm border border-slate-800 focus:ring-2 focus:ring-blue-500 focus:outline-none mb-5 resize-none shadow-inner"
            />
            
            <div className="flex items-stretch gap-2 @2xl:gap-3 justify-end">
              <button 
                onClick={(e) => confirmDeleteVariation(e, activeVariationId)}
                disabled={!activeVariationId}
                className="flex items-center justify-center gap-2 px-3 @2xl:px-5 bg-white border border-rose-200 text-rose-600 rounded-lg font-bold text-[13px] hover:bg-rose-50 transition-colors shadow-sm disabled:opacity-50"
                title="Remove"
              >
                <Trash2 size={16} /> <span className="hidden @2xl:inline">REMOVE</span>
              </button>
              <button 
                onClick={() => handleRegenerate(activeVariationId)}
                disabled={isRegenerating || isGroupGenerating || !activeVariationId}
                className={clsx(
                  "flex items-center justify-center gap-2.5 px-4 @2xl:px-6 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg font-bold text-[13px] hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50 leading-tight tracking-wide",
                  (isRegenerating || isGroupGenerating) && "blur-[1px] cursor-not-allowed"
                )}
                title="Regenerate Variation"
              >
                {isRegenerating || isGroupGenerating ? <Loader2 size={16} className="animate-spin" /> : <RefreshCcw size={16} />}
                <div className="text-left hidden @2xl:block">
                  <div>REGENERATE</div>
                  <div>VARIATION</div>
                </div>
              </button>
              <button 
                onClick={() => handleApprove(activeVariationId)}
                disabled={!activeVariationId}
                className="flex items-center justify-center gap-2.5 px-4 @2xl:px-6 py-2 bg-slate-800 text-white rounded-lg font-bold text-[13px] hover:bg-slate-900 transition-colors shadow-sm disabled:opacity-50 leading-tight tracking-wide"
                title="Approve Asset"
              >
                <CheckCircle size={16} />
                <div className="text-left hidden @2xl:block">
                  <div>APPROVE</div>
                  <div>ASSET</div>
                </div>
              </button>
            </div>
          </div>
        </div>



      </div>

      {/* RIGHT PANEL: Variations */}
      <div className="w-[280px] shrink-0 flex flex-col bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <div className="text-xs font-bold text-slate-500 tracking-wider flex items-center gap-2">
            <Layers size={14} />
            VARIATIONS ({variations.length})
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-5 bg-slate-50">
          <div className="grid grid-cols-2 gap-4 pb-8">
            {variations.map((variation) => (
              <div 
                key={variation.id} 
                onClick={() => (variation.status !== 'generating' && variation.status !== 'failed') && setSelectedVariationId(variation.id)}
                className={clsx(
                  "aspect-square rounded-lg border-2 cursor-pointer overflow-hidden transition-all bg-white relative group flex items-center justify-center",
                  variation.id === activeVariationId && variation.status !== 'failed'
                    ? "border-primary ring-2 ring-primary ring-opacity-20 shadow-md" 
                    : "border-transparent hover:border-slate-300 shadow-sm",
                  variation.status === 'generating' && "opacity-70 cursor-not-allowed",
                  variation.status === 'failed' && "border-rose-200 cursor-default"
                )}
              >
                {variation.status === 'generating' ? (
                  <div className="flex flex-col items-center justify-center text-slate-400 p-2 text-center">
                    <Loader2 className="animate-spin mb-2" size={20} />
                    <span className="text-[10px] font-bold tracking-wider text-slate-400">GENERATING</span>
                  </div>
                ) : variation.status === 'failed' ? (
                  <div className="flex flex-col items-center justify-center text-rose-400 p-2 text-center bg-rose-50 w-full h-full relative group/failed">
                    <XCircle className="mb-2 text-rose-500" size={20} />
                    <span className="text-[10px] font-bold tracking-wider text-rose-500">FAILED</span>
                    
                    {/* Delete button overlay for failed */}
                    <button
                      onClick={(e) => confirmDeleteVariation(e, variation.id)}
                      className="absolute top-1 right-1 bg-black/60 hover:bg-rose-600 text-white p-1.5 rounded-md opacity-0 group-hover/failed:opacity-100 transition-all z-10"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ) : (
                  <>
                    <img 
                      src={`http://localhost:8000/${variation.url}`} 
                      alt="Variation" 
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.onerror = null; e.target.src = variation.url; }}
                    />
                    
                    {/* Delete button overlay */}
                    <button
                      onClick={(e) => confirmDeleteVariation(e, variation.id)}
                      className="absolute top-1 right-1 bg-black/60 hover:bg-rose-600 text-white p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-all z-10"
                    >
                      <Trash2 size={12} />
                    </button>
                    
                    {variation.status === 'approved' && (
                      <div className="absolute top-1 left-1 bg-emerald-500 text-white p-1 rounded-full shadow-sm z-10">
                        <CheckCircle size={12} />
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
          
          {/* Metadata Section - Bottom Right */}
          {activeVariation && (
            <div className="p-6 border-t border-slate-200 bg-white mt-auto">
              <h3 className="text-[13px] font-bold text-slate-500 uppercase tracking-wider mb-5">Asset Metadata</h3>
              <div className="space-y-4 text-[15px]">
                <div className="flex justify-between items-start gap-4">
                  <span className="text-slate-500 flex-shrink-0">File</span>
                  <span className="font-semibold text-slate-800 break-all text-right leading-tight">{activeVariation.asset_name}</span>
                </div>
                {activeVariation.metadata && (
                  <>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Type</span>
                      <span className="font-semibold text-slate-800">{activeVariation.metadata.type}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Ratio</span>
                      <span className="font-semibold text-slate-800">{activeVariation.metadata.ratio}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500">Size</span>
                      <span className="font-semibold text-slate-800">{activeVariation.metadata.size_kb} KB</span>
                    </div>
                    {activeVariation.metadata.created_on && (
                      <div className="flex justify-between items-center mt-3 pt-3 border-t border-slate-100">
                        <span className="text-slate-500 text-xs">Created On</span>
                        <span className="font-semibold text-slate-700 text-xs">{activeVariation.metadata.created_on}</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
        
          {/* Bottom Right Actions */}
          <div className="p-4 border-t border-slate-200 bg-white mt-auto shrink-0">
            <button 
              onClick={() => handleFinish(activeJobId)}
              className="w-full bg-slate-800 text-white flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm hover:bg-slate-900 transition-colors"
            >
              <CheckCircle size={16} />
              FINISH AND APPROVE
            </button>
          </div>
        </div>
        </>
      )}
      
      {/* Fullscreen Overlay */}
      {isFullscreen && activeVariation && (
        <div className="fixed inset-0 z-50 bg-black/90 flex flex-col items-center justify-center backdrop-blur-sm">
          <div className="absolute top-4 right-4 flex items-center gap-4">
            <button 
              onClick={() => setIsFullscreen(false)}
              className="text-white/70 hover:text-white p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
            >
              <X size={24} />
            </button>
          </div>
          
          <button 
            onClick={(e) => { e.stopPropagation(); handlePrev(); }}
            disabled={currentAssetIndex === 0}
            className="absolute left-8 z-10 w-14 h-14 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center text-white disabled:opacity-20 transition-colors"
          >
            <ChevronLeft size={32} />
          </button>

          <img 
            src={`http://localhost:8000/${activeVariation.url}`} 
            alt="Fullscreen preview" 
            className="max-h-[90vh] max-w-[90vw] object-contain shadow-2xl rounded-sm"
          />

          <button 
            onClick={(e) => { e.stopPropagation(); handleNext(); }}
            disabled={currentAssetIndex === activeAssets.length - 1}
            className="absolute right-8 z-10 w-14 h-14 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center text-white disabled:opacity-20 transition-colors"
          >
            <ChevronRight size={32} />
          </button>
          
          <div className="absolute bottom-8 px-6 py-3 bg-black/60 rounded-full text-white font-medium tracking-wide">
            {currentAsset?.variation_group.toUpperCase()} — {activeVariation.asset_name}
          </div>
        </div>
      )}

      {/* Stop Modal */}
      {showStopModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex flex-col items-center justify-center backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <h3 className="text-xl font-bold text-slate-800">Stop Generation</h3>
              <p className="text-sm text-slate-500 mt-2">
                Do you want to completely abort this task, or return it to JSON Review?
              </p>
            </div>
            <div className="p-6 bg-slate-50 flex flex-col gap-3">
              <button 
                onClick={() => handleStop(stopJobId)}
                className="w-full text-left px-4 py-3 bg-white border border-amber-200 rounded-lg text-sm font-bold text-amber-600 hover:bg-amber-50 hover:border-amber-300 transition-colors shadow-sm flex flex-col gap-1"
              >
                <span>Stop Further Generation</span>
                <span className="text-xs font-normal text-amber-500">Keep generated images but stop making new ones.</span>
              </button>
              <button 
                onClick={() => handleAbort(stopJobId)}
                className="w-full text-left px-4 py-3 bg-white border border-rose-200 rounded-lg text-sm font-bold text-rose-600 hover:bg-rose-50 hover:border-rose-300 transition-colors shadow-sm flex flex-col gap-1"
              >
                <span>Abort Task entirely</span>
                <span className="text-xs font-normal text-rose-500">Deletes images and aborts workflow.</span>
              </button>
              <button 
                onClick={() => handleRevert(stopJobId)}
                className="w-full text-left px-4 py-3 bg-white border border-slate-300 rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-100 hover:border-slate-400 transition-colors shadow-sm flex flex-col gap-1"
              >
                <span>Return to JSON Review</span>
                <span className="text-xs font-normal text-slate-500">Deletes images and returns to previous step.</span>
              </button>
              <button 
                onClick={() => setShowStopModal(false)}
                className="w-full text-center px-4 py-2 mt-2 text-sm font-bold text-slate-500 hover:text-slate-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Delete Variation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex flex-col items-center justify-center backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 flex flex-col items-center text-center">
              <div className="w-12 h-12 bg-rose-100 text-rose-500 rounded-full flex items-center justify-center mb-4">
                <Trash2 size={24} />
              </div>
              <h3 className="text-xl font-bold text-slate-800">Remove Variation</h3>
              <p className="text-sm text-slate-500 mt-2">
                Are you sure you want to permanently delete this generated image variation? This action cannot be undone.
              </p>
            </div>
            
            <div className="p-4 bg-slate-50 flex justify-end gap-3">
              <button 
                onClick={() => { setShowDeleteModal(false); setVariationToDelete(null); }}
                className="px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-200 bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={executeDeleteVariation}
                className="px-5 py-2.5 text-sm font-semibold text-white bg-rose-500 hover:bg-rose-600 rounded-lg shadow-sm transition-colors"
              >
                Delete Variation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
