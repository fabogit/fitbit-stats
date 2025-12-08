import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "./store";
import { fetchHealthData } from "./features/dashboard/dashboardSlice";

function App() {
  const dispatch = useAppDispatch();
  const { data, status, error } = useAppSelector((state) => state.dashboard);

  useEffect(() => {
    dispatch(fetchHealthData());
  }, [dispatch]);

  if (status === "loading")
    return <div className="p-10 text-white">Loading data...</div>;
  if (status === "failed")
    return <div className="p-10 text-red-500">Error: {error}</div>;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-8">
      <h1 className="text-3xl font-bold mb-4">Fitbit V2 Check</h1>
      <p>Data Status: {status}</p>
      <p>Records Loaded: {data.length}</p>

      {data.length > 0 && (
        <pre className="bg-slate-900 p-4 rounded mt-4 text-xs overflow-auto max-h-96">
          {JSON.stringify(data[0], null, 2)}
        </pre>
      )}
    </div>
  );
}

export default App;
