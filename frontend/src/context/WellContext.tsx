"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Well } from "@/types/api";
import { fetchWells, createWell, updateWell, deleteWell } from "@/lib/api";

interface WellContextType {
  wells: Well[];
  selectedWellCode: string;
  selectedWell: Well | undefined;
  isLoading: boolean;
  setSelectedWellCode: (code: string) => void;
  refreshWells: () => Promise<void>;
  addWell: (payload: {
    well_code: string;
    field_name: string;
    status?: string;
    config?: { wc_threshold?: number };
  }) => Promise<Well>;
  editWell: (
    wellCode: string,
    updates: { field_name?: string; status?: string; wc_threshold?: number }
  ) => Promise<Well>;
  removeWell: (wellCode: string) => Promise<void>;
}

const WellContext = createContext<WellContextType | undefined>(undefined);

export function WellProvider({ children }: { children: React.ReactNode }) {
  const [wells, setWells] = useState<Well[]>([]);
  const [selectedWellCode, setSelectedWellCode] = useState<string>("WELL-001");
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshWells = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await fetchWells();
      setWells(data);
      if (data.length > 0) {
        setSelectedWellCode((current) => {
          const exists = data.some((w) => w.well_code === current);
          return exists ? current : data[0].well_code;
        });
      }
    } catch (err) {
      console.error("Failed to load wells:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshWells();
  }, [refreshWells]);

  const addWell = async (payload: {
    well_code: string;
    field_name: string;
    status?: string;
    config?: { wc_threshold?: number };
  }) => {
    const newWell = await createWell(payload);
    await refreshWells();
    setSelectedWellCode(newWell.well_code);
    return newWell;
  };

  const editWell = async (
    wellCode: string,
    updates: { field_name?: string; status?: string; wc_threshold?: number }
  ) => {
    const updated = await updateWell(wellCode, updates);
    await refreshWells();
    return updated;
  };

  const removeWell = async (wellCode: string) => {
    await deleteWell(wellCode);
    const data = await fetchWells();
    setWells(data);
    if (data.length > 0) {
      setSelectedWellCode((curr) => {
        if (curr === wellCode) {
          return data[0].well_code;
        }
        return curr;
      });
    }
  };

  const selectedWell = wells.find((w) => w.well_code === selectedWellCode);

  return (
    <WellContext.Provider
      value={{
        wells,
        selectedWellCode,
        selectedWell,
        isLoading,
        setSelectedWellCode,
        refreshWells,
        addWell,
        editWell,
        removeWell,
      }}
    >
      {children}
    </WellContext.Provider>
  );
}

export function useWell() {
  const context = useContext(WellContext);
  if (!context) {
    throw new Error("useWell must be used within a WellProvider");
  }
  return context;
}
