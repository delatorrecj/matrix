import React from "react";

interface GlossaryTooltipProps {
  term: string;
  definition: string;
}

export function GlossaryTooltip({ term, definition }: GlossaryTooltipProps) {
  return (
    <span className="group relative inline-block border-b border-dashed border-primary/50 cursor-help print:border-black">
      <span className="text-primary/90 font-medium print:text-black">{term}</span>
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden w-48 p-2 text-xs text-white bg-gray-900 rounded shadow-lg group-hover:block z-50 print:hidden">
        {definition}
        <svg
          className="absolute text-gray-900 h-2 w-full left-0 top-full"
          x="0px"
          y="0px"
          viewBox="0 0 255 255"
          xmlSpace="preserve"
        >
          <polygon className="fill-current" points="0,0 127.5,127.5 255,0" />
        </svg>
      </span>
    </span>
  );
}
