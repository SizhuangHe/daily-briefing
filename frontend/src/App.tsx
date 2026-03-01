import { Routes, Route } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import DashboardPage from "./components/Dashboard/DashboardPage";
import SettingsPage from "./components/Settings/SettingsPage";

function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </MainLayout>
  );
}

export default App;
