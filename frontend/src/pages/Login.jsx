import React from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, UserCog, User } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 p-6">
      <div className="bg-white max-w-md w-full rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 text-center border-b border-slate-100">
          <h1 className="text-2xl font-bold text-slate-800">Active Fitness</h1>
          <p className="text-sm text-slate-500 mt-1">Product Enrichment Pipeline</p>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm font-medium text-slate-700 text-center mb-4">
            Select a role to continue (Mock Auth)
          </p>
          
          <button 
            onClick={() => login('SUPERADMIN')}
            className="w-full flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:border-primary hover:bg-indigo-50 transition-colors text-left group"
          >
            <div className="flex items-center gap-3">
              <ShieldCheck className="text-indigo-600" size={24} />
              <div>
                <p className="font-semibold text-slate-800 group-hover:text-primary">Super Admin</p>
                <p className="text-xs text-slate-500">Full access, settings, user management</p>
              </div>
            </div>
          </button>

          <button 
            onClick={() => login('ADMIN')}
            className="w-full flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:border-emerald-500 hover:bg-emerald-50 transition-colors text-left group"
          >
            <div className="flex items-center gap-3">
              <UserCog className="text-emerald-600" size={24} />
              <div>
                <p className="font-semibold text-slate-800 group-hover:text-emerald-700">Admin</p>
                <p className="text-xs text-slate-500">Create tasks, approve data & images</p>
              </div>
            </div>
          </button>

          <button 
            onClick={() => login('NORMALUSER')}
            className="w-full flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left group"
          >
            <div className="flex items-center gap-3">
              <User className="text-blue-600" size={24} />
              <div>
                <p className="font-semibold text-slate-800 group-hover:text-blue-700">Normal User</p>
                <p className="text-xs text-slate-500">Create jobs and download completed bundles</p>
              </div>
            </div>
          </button>

        </div>
      </div>
    </div>
  );
}
