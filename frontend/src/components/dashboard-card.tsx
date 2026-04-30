"use client";

import { motion } from "framer-motion";

type Props = {
  label: string;
  value: string | number;
};

export function DashboardCard({ label, value }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-white/10 bg-zinc-900/80 p-5 shadow-lg"
    >
      <p className="text-sm text-zinc-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
    </motion.div>
  );
}
