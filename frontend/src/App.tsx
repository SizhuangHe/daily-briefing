import { Routes, Route } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import DashboardPage from "./components/Dashboard/DashboardPage";
import DevPage from "./components/Dev/DevPage";
import LikedPage from "./components/Liked/LikedPage";
import SettingsPage from "./components/Settings/SettingsPage";

function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/liked" element={<LikedPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/dev" element={<DevPage />} />
      </Routes>
    </MainLayout>
  );
}

export default App;
