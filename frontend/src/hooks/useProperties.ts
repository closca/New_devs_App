import { useCallback, useEffect, useState } from 'react';
import { SecureAPI } from '../lib/secureApi';

/** A property as returned by GET /api/v1/properties (tenant-scoped on the server). */
export interface Property {
  id: string;
  name: string;
  timezone: string;
}

interface UsePropertiesResult {
  properties: Property[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Loads the properties that belong to the signed-in user's tenant.
 * The list is never hardcoded client-side: property ids are only unique per tenant,
 * so the server decides what the caller is allowed to see.
 */
export function useProperties(): UsePropertiesResult {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await SecureAPI.getProperties();
        if (cancelled) return;
        const items: Property[] = Array.isArray(result?.data) ? result.data : [];
        setProperties(items);
      } catch (err) {
        if (cancelled) return;
        console.error('[useProperties] Failed to load properties', err);
        setProperties([]);
        setError('Failed to load properties');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const refetch = useCallback(async () => {
    setReloadToken((t) => t + 1);
  }, []);

  return { properties, loading, error, refetch };
}
