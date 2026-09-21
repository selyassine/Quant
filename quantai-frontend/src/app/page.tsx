'use client';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Sidebar } from '@/components/layout/Sidebar';
import LoginPage from '@/components/LoginPage';
import Dashboard     from '@/components/Dashboard';
import MarketPage    from '@/components/MarketPage';
import PredictPage   from '@/components/PredictPage';
import PortfolioPage from '@/components/PortfolioPage';
import BacktestPage  from '@/components/BacktestPage';
import ExplainPage from '@/components/ExplainPage';
import NewsPage from '@/components/NewsPage';
import PaperTradingPage from '@/components/PaperTradingPage';
import StrategyPage from '@/components/StrategyPage';
import AnalyticsPage from '@/components/AnalyticsPage';
import MLOpsPage from '@/components/MLOpsPage';
import ReportPage from '@/components/ReportPage';
import RealtimePage from '@/components/RealtimePage';
import AssistantPage from '@/components/AssistantPage';
import AgentPage     from '@/components/AgentPage';



const PAGES: Record<string, React.ComponentType> = {
  dashboard: Dashboard,
  market:    MarketPage,
  predict:   PredictPage,
  portfolio: PortfolioPage,
  backtest:  BacktestPage,
  explain:   ExplainPage,
  news:      NewsPage,
  paper: PaperTradingPage,
  strategy: StrategyPage,
  analytics: AnalyticsPage,
  mlops: MLOpsPage,
  report: ReportPage,
  realtime: RealtimePage,
  assistant: AssistantPage,
  agent:     AgentPage,
};

export default function Home() {
  const { isAuthenticated } = useAuth();
  const [page, setPage] = useState('dashboard');
  const Page = PAGES[page] || Dashboard;

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar page={page} setPage={setPage} />
      <main className="flex-1 overflow-y-auto bg-bg">
        <Page />
      </main>
    </div>
  );
}
