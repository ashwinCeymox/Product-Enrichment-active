import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check local storage for mocked user session on load
    const storedUser = localStorage.getItem('active_user');
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const login = (role) => {
    // Mock login based on role selected
    let userData = { name: '', role: '', email: '' };
    if (role === 'SUPERADMIN') {
      userData = { name: 'Super Admin', role: 'SUPERADMIN', email: 'super@activefitness.com' };
    } else if (role === 'ADMIN') {
      userData = { name: 'Pipeline Admin', role: 'ADMIN', email: 'admin@activefitness.com' };
    } else {
      userData = { name: 'Normal User', role: 'NORMALUSER', email: 'user@activefitness.com' };
    }
    
    setUser(userData);
    localStorage.setItem('active_user', JSON.stringify(userData));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('active_user');
  };

  if (loading) {
    return <div className="h-screen w-full flex items-center justify-center bg-slate-50 text-slate-500">Loading session...</div>;
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
