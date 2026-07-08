import React, { useState, useEffect } from 'react';
import api from '../api/client';
import clsx from 'clsx';
import { Search, Loader2, Check, Download, Save, Globe, ExternalLink, Maximize, Minimize } from 'lucide-react';

export default function BundleReview() {
  const [bundles, setBundles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedJob, setSelectedJob] = useState(null);
  
  // Editor state
  const [jsonData, setJsonData] = useState('');
  const [activeTab, setActiveTab] = useState('ai_page'); // 'json', 'table', 'original', 'ai_page'
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const fetchBundles = async () => {
    setLoading(true);
    try {
      const res = await api.get('/jobs/?status=success');
      setBundles(res.data.jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBundles();
  }, []);

  const handleSelectJob = (job) => {
    setSelectedJob(job);
    setJsonData(JSON.stringify(job.product_data || {}, null, 2));
    setActiveTab('ai_page');
  };

  const handleSaveChanges = async () => {
    if (!selectedJob) return;
    setSaving(true);
    try {
      let parsedData = {};
      try { 
        parsedData = JSON.parse(jsonData); 
      } catch(e) { 
        alert('Invalid JSON format!'); 
        setSaving(false); 
        return; 
      }
      // Re-using the approve endpoint to save product data
      await api.post(`/jobs/${selectedJob.id}/update_data`, { product_data: parsedData });
      alert('Changes saved successfully');
      
      const updatedJob = { ...selectedJob, product_data: parsedData };
      setSelectedJob(updatedJob);
      setBundles(bundles.map(b => b.id === updatedJob.id ? updatedJob : b));
    } catch (err) {
      console.error(err);
      alert('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleFinalizeAndSave = async () => {
    if (!selectedJob) return;
    setDownloading(true); // Using this state for the button spinner
    try {
      let parsedData;
      try {
        parsedData = JSON.parse(jsonData);
      } catch (e) {
        alert('Invalid JSON format. Please fix errors before saving.');
        setDownloading(false);
        return;
      }
      
      // Save the final approved data with the finalized flag
      await api.post(`/jobs/${selectedJob.id}/finalize`, { product_data: parsedData });
      
      const newBundles = bundles.filter(b => b.id !== selectedJob.id);
      setBundles(newBundles);
      setSelectedJob(null);
      
      alert('Bundle Finalized and Saved successfully! It has been moved to the Downloads tab.');
      
    } catch (err) {
      console.error(err);
      alert('Failed to finalize bundle.');
    } finally {
      setDownloading(false);
    }
  };

  const filteredBundles = bundles.filter(b => 
    !b.product_data?._bundle_finalized &&
    (b.task_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    (b.url && b.url.toLowerCase().includes(searchQuery.toLowerCase())))
  );

  return (
    <div className="flex h-full bg-slate-50 overflow-hidden text-sm">
      {/* Sidebar */}
      <div className="w-64 flex-shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div className="p-3 border-b border-slate-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Search bundles..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-100 border-transparent focus:bg-white focus:border-primary focus:ring-2 focus:ring-primary/20 rounded-md text-sm transition-all"
            />
          </div>
        </div>
        
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
          <span className="text-xs font-bold text-slate-500 tracking-wider">APPROVED BUNDLES</span>
          <span className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs font-bold">{bundles.length}</span>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-8 text-center text-slate-500 flex flex-col items-center">
              <Loader2 className="animate-spin mb-2 text-slate-400" size={24} />
              Loading bundles...
            </div>
          ) : filteredBundles.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              No bundles found.
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {filteredBundles.map(job => {
                const isActive = selectedJob?.id === job.id;
                const taskName = job.task_name || "Unknown Task";
                const prodName = job.product_data?.product_identity?.product_name || job.product_data?.product_identity?.brand || "Unknown Product";
                
                return (
                  <li key={job.id}>
                    <button
                      onClick={() => handleSelectJob(job)}
                      className={clsx(
                        "w-full text-left p-3 hover:bg-slate-50 transition-colors focus:outline-none flex flex-col gap-1",
                        isActive ? "bg-indigo-50/50 border-l-4 border-primary" : "border-l-4 border-transparent"
                      )}
                    >
                      <div className="flex justify-between items-start w-full">
                        <h4 className="font-semibold text-slate-800 text-sm truncate pr-2">{taskName}</h4>
                        {isActive && <span className="bg-green-100 text-green-700 text-[9px] font-bold px-1.5 py-0.5 rounded uppercase shrink-0">Active</span>}
                      </div>
                      <p className="text-xs text-slate-500 truncate" title={prodName}>{prodName}</p>
                      <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                        <Check size={10} /> Updated {new Date(job.updated_at).toLocaleDateString()}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Action Panel */}
        {selectedJob && (
          <div className="p-4 bg-white border-t border-slate-200 flex flex-col gap-3 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
            <div>
              <h5 className="text-[10px] font-bold text-slate-500 tracking-wider mb-2">PRODUCT SUMMARY</h5>
              <div className="text-xs">
                <div className="mb-1"><span className="text-slate-400 text-[10px]">TASK NAME:</span><br/><span className="font-medium text-slate-700 truncate block">{selectedJob.task_name}</span></div>
                <div><span className="text-slate-400 text-[10px]">BRAND:</span><br/><span className="font-medium text-slate-700 truncate block">{selectedJob.product_data?.product_identity?.brand || "Unknown"}</span></div>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <button
                onClick={handleSaveChanges}
                disabled={saving || downloading}
                className="w-full py-2 px-3 bg-white border border-slate-300 text-slate-700 rounded-md text-xs font-semibold hover:bg-slate-50 transition-colors flex justify-center items-center gap-2"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                SAVE CHANGES
              </button>
              <button
                onClick={handleFinalizeAndSave}
                disabled={saving || downloading}
                className="w-full py-2 px-3 bg-primary text-white rounded-md text-xs font-semibold hover:bg-primary/90 transition-colors flex justify-center items-center gap-2"
              >
                {downloading ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                FINALIZE AND SAVE
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full bg-slate-100 overflow-hidden relative">
        {!selectedJob ? (
          <div className="flex-1 flex items-center justify-center flex-col text-slate-400">
            <Globe size={48} className="mb-4 opacity-20" />
            <h2 className="text-xl font-medium text-slate-500">Select a bundle to review</h2>
            <p className="text-sm mt-2">Choose an approved product from the sidebar.</p>
          </div>
        ) : (
          <>
            {/* Tabs */}
            <div className="bg-white border-b border-slate-200 px-6 pt-4 flex justify-between items-end shrink-0">
              <div className="flex gap-6">
                {[
                  { id: 'json', label: 'Edit Generated JSON' },
                  { id: 'table', label: 'Table View' },
                  { id: 'original', label: 'Product Page' },
                  { id: 'ai_page', label: '✨ AI GENERATED PAGE' },
                ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    "pb-3 text-sm font-medium border-b-2 transition-colors relative top-[1px]",
                    activeTab === tab.id 
                      ? "border-primary text-primary" 
                      : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                  )}
                >
                  {tab.id === 'ai_page' && activeTab === tab.id ? (
                    <span className="bg-primary text-white px-2 py-1 rounded shadow-sm text-xs ml-1 mr-1">{tab.label}</span>
                  ) : tab.label}
                </button>
              ))}
              </div>
              
              {activeTab === 'ai_page' && (
                <button 
                  onClick={() => setIsFullscreen(true)} 
                  className="mb-3 text-slate-500 hover:text-primary flex items-center gap-1.5 text-sm font-semibold transition-colors"
                  title="View Fullscreen"
                >
                  <Maximize size={16} /> <span className="hidden xl:inline">Fullscreen</span>
                </button>
              )}
            </div>

            {/* Tab Content */}
            <div className="flex-1 p-6 overflow-hidden">
              <div className="h-full bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden relative">
                
                {/* 1. JSON Editor */}
                {activeTab === 'json' && (
                  <textarea 
                    className="w-full h-full font-mono text-sm p-4 resize-none focus:outline-none focus:ring-0 bg-slate-50"
                    value={jsonData}
                    onChange={e => setJsonData(e.target.value)}
                    spellCheck={false}
                  />
                )}

                {/* 2. Table View (Field Editor) */}
                {activeTab === 'table' && (
                  <div className="h-full overflow-auto">
                    {(() => {
                      let parsed = {};
                      try { parsed = JSON.parse(jsonData); } catch (e) { return <div className="p-8 text-red-500 text-center">Invalid JSON</div>; }
                      const keys = Object.keys(parsed);
                      
                      return (
                        <table className="min-w-full divide-y divide-slate-200">
                          <thead className="bg-slate-50 sticky top-0 z-10">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Field</th>
                              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Content</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {keys.map(key => {
                              const val = parsed[key];
                              const isString = typeof val === 'string';
                              return (
                                <tr key={key} className="hover:bg-slate-50">
                                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-700 align-top">
                                    {key}
                                  </td>
                                  <td className="px-6 py-4 text-sm text-slate-600">
                                    {isString ? (
                                      <textarea 
                                        className="w-full min-h-[60px] p-2 border border-slate-300 rounded-md focus:ring-primary focus:border-primary text-sm"
                                        value={val}
                                        onChange={(e) => {
                                          const newData = {...parsed, [key]: e.target.value};
                                          setJsonData(JSON.stringify(newData, null, 2));
                                        }}
                                      />
                                    ) : (
                                      <pre className="bg-slate-100 p-3 rounded-md text-xs overflow-auto max-h-40 border border-slate-200">
                                        {JSON.stringify(val, null, 2)}
                                      </pre>
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

                {/* 3. Original Product Page */}
                {activeTab === 'original' && (
                  <div className="h-full w-full flex flex-col bg-slate-50">
                    <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0 shadow-sm z-10">
                      <div className="flex items-center gap-3">
                        <div className="bg-primary/10 p-2 rounded-lg text-primary">
                          <Globe size={20} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-800 text-sm">Original Source</h3>
                          <p className="text-xs text-slate-500 truncate max-w-md" title={selectedJob.url}>{selectedJob.url}</p>
                        </div>
                      </div>
                      <a 
                        href={selectedJob.url} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="flex items-center gap-2 bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-slate-700 transition-colors shadow-sm"
                      >
                        Open in New Tab <ExternalLink size={14} />
                      </a>
                    </div>
                    
                    <div className="flex-1 w-full bg-slate-100 relative">
                       {/* Overlay hint if blocked */}
                       <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none opacity-60 px-6 z-0">
                          <Globe size={48} className="text-slate-300 mb-4" />
                          <p className="text-slate-500 text-sm max-w-md text-center bg-slate-100/90 p-4 rounded-xl border border-slate-200">
                            <strong>Is the page blank or showing a connection error?</strong><br/><br/>
                            Many modern e-commerce sites (like Shopify) strictly block their pages from being embedded in other apps for security reasons.<br/><br/>
                            Please use the <b>Open in New Tab</b> button above to view the source.
                          </p>
                       </div>
                       
                      {selectedJob.url ? (
                        <iframe 
                          src={`${api.defaults.baseURL}/jobs/proxy?url=${encodeURIComponent(selectedJob.url)}`} 
                          className="w-full h-full border-none relative z-10 bg-white"
                          title="Original Product Page"
                          sandbox="allow-same-origin allow-scripts allow-popups"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-slate-400 relative z-10">No URL available</div>
                      )}
                    </div>
                  </div>
                )}

                {/* 4. AI Generated Page (Active Fitness Theme) */}
                {activeTab === 'ai_page' && (
                  <ActiveFitnessPreview productData={selectedJob.product_data} />
                )}

              </div>
            </div>
          </>
        )}
      </div>

      {/* Fullscreen AI Preview Overlay */}
      {isFullscreen && activeTab === 'ai_page' && selectedJob && (
        <div className="fixed inset-0 z-[100] bg-white flex flex-col">
          <div className="bg-slate-900 text-white px-6 py-3 flex justify-between items-center shrink-0">
            <div className="font-semibold text-sm flex items-center gap-2">
              <span className="text-xl">✨</span> AI Generated Page Preview
            </div>
            <button 
              onClick={() => setIsFullscreen(false)} 
              className="hover:bg-slate-800 px-3 py-1.5 rounded-md transition-colors flex items-center gap-2 text-sm font-semibold border border-slate-700"
            >
              <Minimize size={16} /> Exit Fullscreen
            </button>
          </div>
          <div className="flex-1 overflow-hidden relative">
            <ActiveFitnessPreview productData={selectedJob.product_data} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── ACTIVE FITNESS STORE Theme Styled Preview ─────────────────────────
function ActiveFitnessPreview({ productData }) {
  if (!productData) return <div className="p-8 text-center text-slate-400">No Product Data</div>;

  const identity = productData.product_identity || {};
  const images = productData.images || {};
  const pricing = productData.pricing || {};
  const features = productData.key_features || [];
  const about = productData.about_this_item || [];
  const specs = productData.specifications || {};
  const faqs = productData.faqs || [];
  
  const [activeTab, setActiveTab] = useState('specs');

  // Helper to construct usable image URL for UI
  const resolveImageUrl = (img) => {
    if (!img) return '';
    if (img.url && img.url.startsWith('http')) return img.url;
    const path = img.local_path || img.url;
    if (path) {
      return `${api.defaults.baseURL}/images/serve?path=${encodeURIComponent(path)}`;
    }
    return 'https://placehold.co/600x600/f1f5f9/94a3b8?text=No+Image';
  };

  const heroImage = resolveImageUrl(images.scraped_images?.[0]) || resolveImageUrl(images.lifestyle_images?.[0]) || 'https://placehold.co/600x600/f1f5f9/94a3b8?text=No+Image';
  const allImages = [...(images.scraped_images || []), ...(images.lifestyle_images || []), ...(images.feature_images || [])];
  
  const [activeIndex, setActiveIndex] = useState(0);
  const activeImage = allImages.length > 0 ? resolveImageUrl(allImages[activeIndex]) : heroImage;

  const handleNextImage = () => {
    if (allImages.length > 0) {
      setActiveIndex((prev) => (prev + 1) % allImages.length);
    }
  };

  const handlePrevImage = () => {
    if (allImages.length > 0) {
      setActiveIndex((prev) => (prev - 1 + allImages.length) % allImages.length);
    }
  };

  return (
    <div className="h-full overflow-y-auto font-sans bg-white text-[#1a1a1a]">
      {/* Top Header */}
      <header className="flex items-center justify-between px-8 py-3.5 border-b border-[#e2e2e2] gap-6 sticky top-0 bg-white z-50">
        <div className="flex items-center">
          <img src="/active_fitness_logo.png" alt="Active Fitness Store" className="h-[42px] object-contain" />
        </div>
        <div className="hidden md:flex flex-1 max-w-[760px] items-center gap-2.5 bg-[#f7f7f7] border border-[#e2e2e2] rounded-md px-3.5 py-2.5 text-[#555555]">
          <Search size={16} />
          <input type="text" placeholder="Shop From 15000+ Products" className="border-none bg-transparent outline-none flex-1 text-[13px] text-[#1a1a1a]" disabled />
        </div>
        <div className="flex items-center gap-6 text-[12px] font-bold tracking-wide whitespace-nowrap text-[#1a1a1a]">
          <div className="hidden lg:flex items-center gap-1.5 cursor-pointer">📍 STORE LOCATIONS</div>
          <div className="flex items-center gap-1.5 cursor-pointer">🌐 EN ▾</div>
          <div className="flex items-center gap-1.5 cursor-pointer">👤 ▾</div>
          <div className="relative flex items-center cursor-pointer">
            🛒
            <span className="absolute -top-2 -right-2.5 bg-[#d5222a] text-white text-[9px] font-extrabold w-4 h-4 rounded-full flex items-center justify-center">0</span>
          </div>
        </div>
      </header>

      {/* Main Nav */}
      <nav className="hidden md:flex items-center gap-8 px-8 py-3.5 border-b border-[#e2e2e2] text-[12.5px] font-extrabold tracking-wide">
        <div className="flex items-center gap-2 cursor-pointer">☰ SHOP BY CATEGORY</div>
        <div className="cursor-pointer hover:text-[#d5222a]">FITNESS</div>
        <div className="cursor-pointer hover:text-[#d5222a]">SPORTS</div>
        <div className="cursor-pointer hover:text-[#d5222a]">WELLNESS</div>
        <div className="cursor-pointer hover:text-[#d5222a]">PERFORMANCE</div>
        <div className="cursor-pointer hover:text-[#d5222a]">SALE</div>
        <div className="cursor-pointer hover:text-[#d5222a]">COMMERCIAL</div>
        <div className="ml-auto text-[#d5222a] flex items-center gap-2 cursor-pointer">
          <span className="w-5 h-5 rounded-full bg-[#d5222a] flex items-center justify-center text-white text-[9px]">▶</span> WHAT'S NEW
        </div>
      </nav>

      {/* Breadcrumb */}
      <div className="px-8 pt-4 pb-2 text-[12.5px] text-[#555555]">
        {productData.breadcrumbs?.map((crumb, idx) => (
          <React.Fragment key={idx}>
            <span className="hover:text-[#111111] hover:underline cursor-pointer">{crumb}</span>
            {idx < productData.breadcrumbs.length - 1 && <span className="mx-1.5">/</span>}
          </React.Fragment>
        )) || (
          <><span className="hover:text-[#111111] hover:underline cursor-pointer">Home</span> <span className="mx-1.5">/</span> <span className="hover:text-[#111111] hover:underline cursor-pointer">Fitness</span> <span className="mx-1.5">/</span> <span>{identity.product_name}</span></>
        )}
      </div>

      {/* Product Section */}
      <div className="grid grid-cols-1 lg:grid-cols-[100px_1fr_380px] gap-8 px-8 pt-5 items-start max-w-[1400px] mx-auto">
        
        {/* Thumbnails */}
        <div className="flex lg:flex-col gap-3 overflow-x-auto lg:overflow-y-auto lg:max-h-[600px] order-2 lg:order-1 scrollbar-hide pb-2 lg:pb-0 pr-1">
          {allImages.map((img, i) => (
            <img 
              key={i} 
              src={resolveImageUrl(img)} 
              alt="Thumbnail" 
              onClick={() => setActiveIndex(i)}
              className={clsx(
                "w-[84px] h-[84px] object-cover border rounded-md cursor-pointer shrink-0 transition-all",
                activeIndex === i ? "border-[#111111] border-2" : "border-[#e2e2e2] hover:border-[#8a8a8a]"
              )}
            />
          ))}
        </div>

        {/* Main Gallery */}
        <div className="flex flex-col items-center relative order-1 lg:order-2">
          <div className="self-end mb-1.5 w-[34px] h-[34px] border border-[#e2e2e2] rounded-md bg-white flex items-center justify-center cursor-pointer shadow-sm hover:bg-gray-50">
            🔍
          </div>
          <div className="relative w-full aspect-square bg-[#f7f7f7] rounded-md flex items-center justify-center overflow-hidden border border-[#e2e2e2]">
            <img src={activeImage} alt="Main Product" className="w-full h-full object-contain mix-blend-multiply" />
            <button onClick={handlePrevImage} className="absolute left-2.5 top-1/2 -translate-y-1/2 w-[34px] h-[34px] rounded-full bg-white border border-[#e2e2e2] flex items-center justify-center shadow-sm hover:bg-gray-50 text-[14px]">‹</button>
            <button onClick={handleNextImage} className="absolute right-2.5 top-1/2 -translate-y-1/2 w-[34px] h-[34px] rounded-full bg-white border border-[#e2e2e2] flex items-center justify-center shadow-sm hover:bg-gray-50 text-[14px]">›</button>
          </div>
          <div className="flex flex-wrap justify-center gap-1.5 mt-3.5 max-w-[80%] mx-auto">
            {allImages.map((img, i) => (
              <span key={i} onClick={() => setActiveIndex(i)} className={clsx("w-[34px] h-[3px] rounded-full cursor-pointer hover:bg-[#8a8a8a]", activeIndex === i ? "bg-[#111111]" : "bg-[#e2e2e2]")}></span>
            ))}
          </div>
        </div>

        {/* Buy Box */}
        <div className="order-3 pb-10">
          <h1 className="text-[26px] font-extrabold leading-tight mb-3.5 text-[#111111]">{identity.product_name}</h1>
          <div className="text-[24px] font-extrabold mb-3.5">AED {pricing.price || 'XXX.00'}</div>

          <div className="flex items-center gap-2.5 py-3 border-t border-[#e2e2e2] text-[12.5px] flex-wrap">
            <div className="flex gap-1.5">
              <span className="border border-[#e2e2e2] rounded px-1.5 py-0.5 text-[10px] font-extrabold bg-[#f7f7f7]">BANK</span>
              <span className="border border-[#e2e2e2] rounded px-1.5 py-0.5 text-[10px] font-extrabold bg-[#f7f7f7]">BANK</span>
            </div>
            Bank Offers 0% EMI — Pay AED {pricing.price ? (pricing.price / 6).toFixed(2) : '00.00'} for 6 months.
          </div>
          
          <div className="flex items-center gap-2.5 py-3 border-t border-[#e2e2e2] text-[12.5px] flex-wrap">
            <div className="flex gap-1.5">
              <span className="border border-[#e2e2e2] rounded px-1.5 py-0.5 text-[10px] font-extrabold bg-[#f7f7f7]">tamara</span>
              <span className="border border-[#e2e2e2] rounded px-1.5 py-0.5 text-[10px] font-extrabold bg-[#f7f7f7]">tabby</span>
            </div>
            Split into 3 interest-free payments of AED {pricing.price ? (pricing.price / 3).toFixed(2) : '00.00'}.
          </div>

          <div className="flex items-center gap-2.5 py-3 border-t border-[#e2e2e2] text-[13px]">
            <div className="flex items-center gap-1.5 font-extrabold text-[11px] border border-[#1a1a1a] rounded px-2 py-1">
              🚚 Standard
            </div>
            <span>Estimated delivery: <b>3-5 Business Days</b></span>
          </div>

          {identity.model && (
            <div className="mt-4">
              <div className="font-extrabold text-[13px] mb-2">Model</div>
              <div className="inline-block border border-[#1a1a1a] rounded px-4 py-2 text-[13px] font-semibold bg-white cursor-pointer">{identity.model}</div>
            </div>
          )}

          <div className="text-[#d5222a] font-bold text-[13px] mt-4">Hurry up! Only 2 left in stock</div>

          <div className="flex gap-3.5 mt-2.5">
            <button className="flex-1 py-4 bg-[#111111] text-white rounded text-[13px] font-extrabold tracking-wide hover:bg-[#333] transition-colors">ADD TO CART</button>
            <button className="flex-1 py-4 bg-[#d5222a] text-white rounded text-[13px] font-extrabold tracking-wide hover:bg-[#b81c23] transition-colors">BUY NOW</button>
          </div>

          <div className="flex gap-6 mt-4 text-[12.5px] font-bold text-[#1a1a1a]">
            <div className="flex items-center gap-1.5 cursor-pointer hover:text-[#d5222a]">♡ WISHLIST</div>
            <div className="flex items-center gap-1.5 cursor-pointer hover:text-[#d5222a]">⇄ COMPARE</div>
            <div className="flex items-center gap-1.5 cursor-pointer hover:text-[#d5222a]">⤴ SHARE</div>
          </div>

          <div className="mt-5.5 rounded-md overflow-hidden bg-gradient-to-r from-[#111] via-[#222] to-[#d5222a] text-white p-5 flex items-center justify-between gap-4 mt-6">
            <div>
              <h3 className="m-0 mb-1 text-[17px] font-bold leading-tight">Win Exciting Rewards on Every Order</h3>
              <p className="m-0 text-[12px] opacity-85 leading-tight">Above a qualifying spend threshold — seasonal sale partners</p>
            </div>
            <div className="bg-[#ffcc00] text-[#111] font-black text-[11px] rounded-full w-16 h-16 flex items-center justify-center text-center leading-[1.1] shrink-0">
              100%<br/>CASH<br/>BACK
            </div>
          </div>

          {about.length > 0 && (
            <div className="mt-6 pt-4 border-t border-[#e2e2e2]">
              <h4 className="text-[13px] tracking-wide mb-2 font-bold">ABOUT THIS ITEM</h4>
              <ul className="list-disc pl-4 text-[13px] text-[#555555] mb-2 space-y-1">
                {about.slice(0, 3).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              <a href="#specs-tab" className="text-[#111111] underline text-[13px] font-semibold hover:text-[#d5222a]" onClick={(e) => { e.preventDefault(); setActiveTab('specs'); }}>Learn more</a>
            </div>
          )}

          <div className="flex items-center gap-4 py-4 border-t border-[#e2e2e2] mt-2">
            <div className="w-[46px] h-[46px] border border-[#e2e2e2] rounded flex items-center justify-center font-black text-[11px] bg-[#f7f7f7]">{identity.brand || 'LOGO'}</div>
            <div>
              <div className="text-[12.5px] text-[#555555]">BRAND: <b className="text-[#1a1a1a] text-[13px] block mt-0.5">{identity.brand}</b></div>
              <a href="#" className="text-[12.5px] text-[#111111] underline font-semibold mt-0.5 block hover:text-[#d5222a]">Visit Brand Store</a>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-2">
            <button className="bg-[#f2f2f2] border-none rounded p-3.5 text-[12.5px] font-bold flex items-center justify-center gap-2 hover:bg-[#e2e2e2]">📄 REQUEST PRICE MATCH</button>
            <button className="bg-[#f2f2f2] border-none rounded p-3.5 text-[12.5px] font-bold flex items-center justify-center gap-2 hover:bg-[#e2e2e2]">🔔 SET PRICE DROP ALERT</button>
            <button className="bg-[#f2f2f2] border-none rounded p-3.5 text-[12.5px] font-bold flex items-center justify-center gap-2 col-span-2 hover:bg-[#e2e2e2]">💬 CHAT WITH AN EXPERT</button>
          </div>
        </div>
      </div>

      {/* Tabs Section */}
      <div className="mt-6 px-8 pb-16 max-w-[1400px] mx-auto" id="specs-tab">
        <div className="flex gap-8 border-b border-[#e2e2e2]">
          <div onClick={() => setActiveTab('specs')} className={clsx("py-4 font-extrabold text-[13px] tracking-wide cursor-pointer border-b-2", activeTab === 'specs' ? "text-[#d5222a] border-[#d5222a]" : "text-[#555555] border-transparent hover:text-[#1a1a1a]")}>SPECIFICATIONS</div>
          <div onClick={() => setActiveTab('features')} className={clsx("py-4 font-extrabold text-[13px] tracking-wide cursor-pointer border-b-2", activeTab === 'features' ? "text-[#d5222a] border-[#d5222a]" : "text-[#555555] border-transparent hover:text-[#1a1a1a]")}>FEATURES</div>
          <div onClick={() => setActiveTab('faq')} className={clsx("py-4 font-extrabold text-[13px] tracking-wide cursor-pointer border-b-2", activeTab === 'faq' ? "text-[#d5222a] border-[#d5222a]" : "text-[#555555] border-transparent hover:text-[#1a1a1a]")}>FAQS</div>
          <div onClick={() => setActiveTab('policy')} className={clsx("py-4 font-extrabold text-[13px] tracking-wide cursor-pointer border-b-2", activeTab === 'policy' ? "text-[#d5222a] border-[#d5222a]" : "text-[#555555] border-transparent hover:text-[#1a1a1a]")}>SALES POLICY</div>
        </div>

        <div className="max-w-[900px] pt-8">
          {activeTab === 'specs' && (
            <div>
              <h2 className="text-[22px] font-bold tracking-wide mb-4">SPECIFICATIONS</h2>
              <table className="w-full border-collapse mb-8">
                <tbody>
                  {productData.features_table ? (
                    productData.features_table.map((row, i) => (
                      <tr key={i} className="border-b border-[#e2e2e2] hover:bg-[#f7f7f7]">
                        <td className="py-3.5 text-[13px] text-[#555555] w-[45%] pr-4 capitalize">{row.label}</td>
                        <td className="py-3.5 text-[13px] font-semibold text-[#1a1a1a]">{row.value}</td>
                      </tr>
                    ))
                  ) : (
                    Object.entries(specs).map(([key, val]) => {
                      if (typeof val === 'object' || !val) return null;
                      return (
                        <tr key={key} className="border-b border-[#e2e2e2] hover:bg-[#f7f7f7]">
                          <td className="py-3.5 text-[13px] text-[#555555] w-[45%] pr-4 capitalize">{key.replace(/_/g, ' ')}</td>
                          <td className="py-3.5 text-[13px] font-semibold text-[#1a1a1a]">{val}</td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
              {productData.long_description && (
                 <>
                   <h2 className="text-[22px] font-bold tracking-wide mb-4 mt-8">DESCRIPTION</h2>
                   <p className="text-[13.5px] text-[#1a1a1a] leading-[1.7] whitespace-pre-wrap">{productData.long_description}</p>
                 </>
              )}
            </div>
          )}

          {activeTab === 'features' && (
            <div>
              <h2 className="text-[22px] font-bold tracking-wide mb-6">KEY FEATURES</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {features.map((feat, idx) => {
                  const featImg = images.feature_images?.[idx];
                  return (
                    <div key={idx} className="bg-[#f7f7f7] rounded-lg overflow-hidden border border-[#e2e2e2]">
                      {featImg && (
                         <img src={resolveImageUrl(featImg)} alt={feat.title} className="w-full h-48 object-cover mix-blend-multiply bg-white" />
                      )}
                      <div className="p-5">
                        <h3 className="font-bold text-[16px] mb-2">{feat.title}</h3>
                        <p className="text-[13.5px] text-[#555555] leading-relaxed">{feat.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'faq' && (
            <div>
              <h2 className="text-[22px] font-bold tracking-wide mb-6">FREQUENTLY ASKED QUESTIONS</h2>
              {faqs.length > 0 ? (
                <div className="flex flex-col gap-3">
                  {faqs.map((faq, i) => (
                    <details key={i} className="border border-[#e2e2e2] rounded-md group bg-white shadow-sm overflow-hidden open:bg-[#f7f7f7]">
                      <summary className="p-4 font-bold cursor-pointer list-none flex justify-between items-center text-[14px] outline-none select-none hover:bg-[#f7f7f7]">
                        {faq.question}
                        <span className="text-[#d5222a] text-xl font-light group-open:rotate-45 transition-transform duration-300 ml-4 shrink-0">+</span>
                      </summary>
                      <div className="p-4 pt-0 text-[#555555] text-[13.5px] leading-relaxed border-t border-transparent group-open:border-[#e2e2e2] mt-2">
                        {faq.answer}
                      </div>
                    </details>
                  ))}
                </div>
              ) : (
                <p className="text-[13.5px] text-[#555555]">No FAQs available for this product.</p>
              )}
            </div>
          )}

          {activeTab === 'policy' && (
            <div>
              <h2 className="text-[22px] font-bold tracking-wide mb-4">SALES POLICY</h2>
              <p className="text-[13.5px] text-[#1a1a1a] leading-[1.7]">
                Everything you need to know before and after your purchase — Delivery, Warranty, Returns &amp; Refunds, Cash on Delivery and Installation Details.<br/><br/>
                <a href="#" className="font-bold underline hover:text-[#d5222a]">Read our full policies</a>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
