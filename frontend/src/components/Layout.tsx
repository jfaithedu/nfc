import { ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import useAuth from '../hooks/useAuth';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="sticky top-0 z-10 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 max-w-screen-2xl items-center">
          <div className="mr-4 flex">
            <Link to="/" className="flex items-center space-x-2">
              <span className="font-bold">NFC Music Player</span>
            </Link>
          </div>
          <div className="flex flex-1 items-center space-x-2 justify-between">
            <nav className="flex items-center space-x-4 lg:space-x-6">
              <Link
                to="/"
                className="text-sm font-medium transition-colors hover:text-primary"
              >
                Dashboard
              </Link>
              <Link
                to="/tags"
                className="text-sm font-medium transition-colors hover:text-primary"
              >
                Tags
              </Link>
              <Link
                to="/media"
                className="text-sm font-medium transition-colors hover:text-primary"
              >
                Media
              </Link>
              <Link
                to="/system"
                className="text-sm font-medium transition-colors hover:text-primary"
              >
                System
              </Link>
            </nav>
            <div className="flex items-center">
              <Button 
                variant="ghost" 
                size="sm"
                onClick={handleLogout}
              >
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 container py-6">{children}</main>
      <footer className="py-6 md:px-8 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-14 md:flex-row">
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
            Built for Winston 🎵
          </p>
        </div>
      </footer>
    </div>
  );
}