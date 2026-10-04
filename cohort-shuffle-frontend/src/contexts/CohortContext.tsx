"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { Cohort } from "@/types";
import { fetchMyCohorts } from "@/lib/mocks/cohorts";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CohortContextValue {
  cohorts: Cohort[];
  activeCohort: Cohort | null;
  setActiveCohort: (cohort: Cohort) => void;
  isLoading: boolean;
  /** Call after joining a new cohort to refresh the list. */
  refreshCohorts: () => Promise<void>;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const CohortContext = createContext<CohortContextValue | null>(null);

const ACTIVE_COHORT_KEY = "cohort_shuffle:activeCohortId";

// ─── Provider ─────────────────────────────────────────────────────────────────

export function CohortProvider({ children }: { children: React.ReactNode }) {
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [activeCohort, setActiveCohortState] = useState<Cohort | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadCohorts = useCallback(async () => {
    setIsLoading(true);
    try {
      // Swap fetchMyCohorts() for a real fetch() call when backend is ready.
      const data = await fetchMyCohorts();
      setCohorts(data);

      // Restore last active cohort from localStorage, or default to the first one
      const storedId =
        typeof window !== "undefined"
          ? localStorage.getItem(ACTIVE_COHORT_KEY)
          : null;

      const restored = storedId
        ? data.find((c) => c.id === storedId) ?? null
        : null;

      setActiveCohortState(restored ?? data[0] ?? null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCohorts();
  }, [loadCohorts]);

  const setActiveCohort = useCallback((cohort: Cohort) => {
    setActiveCohortState(cohort);
    if (typeof window !== "undefined") {
      localStorage.setItem(ACTIVE_COHORT_KEY, cohort.id);
    }
  }, []);

  return (
    <CohortContext.Provider
      value={{
        cohorts,
        activeCohort,
        setActiveCohort,
        isLoading,
        refreshCohorts: loadCohorts,
      }}
    >
      {children}
    </CohortContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useCohort(): CohortContextValue {
  const ctx = useContext(CohortContext);
  if (!ctx) {
    throw new Error("useCohort must be used inside <CohortProvider>");
  }
  return ctx;
}
