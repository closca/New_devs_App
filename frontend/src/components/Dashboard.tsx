import React, { useEffect, useState } from "react";
import { RevenueSummary } from "./RevenueSummary";
import { useProperties } from "../hooks/useProperties";

// Seed data lives in March 2024; default the picker there so the dashboard opens on real figures.
const DEFAULT_PERIOD = '2024-03';

const parsePeriod = (period: string) => {
  const [year, month] = period.split('-').map(Number);
  return { year, month };
};

const Dashboard: React.FC = () => {
  // The property list comes from the server, scoped to the signed-in tenant.
  const { properties, loading: propertiesLoading, error: propertiesError } = useProperties();
  const [selectedProperty, setSelectedProperty] = useState('');
  const [selectedPeriod, setSelectedPeriod] = useState(DEFAULT_PERIOD);
  const { year, month } = parsePeriod(selectedPeriod);

  // Pick the first property once the list arrives, and drop a selection that is no longer
  // in the list (e.g. after signing in as a different tenant).
  useEffect(() => {
    if (properties.length === 0) {
      setSelectedProperty('');
      return;
    }
    if (!properties.some((p) => p.id === selectedProperty)) {
      setSelectedProperty(properties[0].id);
    }
  }, [properties, selectedProperty]);

  const noProperties = !propertiesLoading && !propertiesError && properties.length === 0;

  return (
    <div className="p-4 lg:p-6 min-h-full">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Property Management Dashboard</h1>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 lg:p-6">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
              <div>
                <h2 className="text-lg lg:text-xl font-medium text-gray-900 mb-2">Revenue Overview</h2>
                <p className="text-sm lg:text-base text-gray-600">
                  Monthly performance insights for your properties
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                {/* Property Selector */}
                <div className="flex flex-col sm:items-end">
                  <label htmlFor="property-select" className="text-xs font-medium text-gray-700 mb-1">Select Property</label>
                  <select
                    id="property-select"
                    value={selectedProperty}
                    onChange={(e) => setSelectedProperty(e.target.value)}
                    disabled={propertiesLoading || properties.length === 0}
                    className="block w-full sm:w-auto min-w-[200px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm disabled:bg-gray-50 disabled:text-gray-400"
                  >
                    {propertiesLoading && <option value="">Loading properties…</option>}
                    {noProperties && <option value="">No properties for your account</option>}
                    {properties.map((property) => (
                      <option key={property.id} value={property.id}>
                        {property.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Month Selector */}
                <div className="flex flex-col sm:items-end">
                  <label htmlFor="period-select" className="text-xs font-medium text-gray-700 mb-1">Select Month</label>
                  <input
                    id="period-select"
                    type="month"
                    value={selectedPeriod}
                    onChange={(e) => e.target.value && setSelectedPeriod(e.target.value)}
                    className="block w-full sm:w-auto px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {propertiesError && (
              <div className="p-4 text-red-500 bg-red-50 rounded-lg">{propertiesError}</div>
            )}
            {noProperties && (
              <div className="p-4 text-gray-500 bg-gray-50 rounded-lg">
                No properties are linked to your account yet.
              </div>
            )}
            {selectedProperty && (
              <RevenueSummary propertyId={selectedProperty} year={year} month={month} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
