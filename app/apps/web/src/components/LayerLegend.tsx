import { Layers } from "lucide-react";

interface LayerLegendProps {
  layers: {
    id: string;
    label: string;
    icon: React.ElementType;
    active: boolean;
    color?: string;
  }[];
  onToggleLayer: (id: string) => void;
}

export function LayerLegend({ layers, onToggleLayer }: LayerLegendProps) {
  return (
    <div className="bg-surface/90 backdrop-blur shadow-md rounded-lg p-3 border border-border w-64 pointer-events-auto">
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-1 flex items-center gap-2">
        <Layers className="w-3.5 h-3.5" />
        Map Layers
      </h3>
      
      <div className="flex flex-col gap-1.5">
        {layers.map((layer) => {
          const Icon = layer.icon;
          return (
            <button
              key={layer.id}
              onClick={() => onToggleLayer(layer.id)}
              className={`flex items-center justify-between px-2 py-1.5 rounded transition-colors text-sm ${
                layer.active 
                  ? "bg-primary/10 text-primary font-medium" 
                  : "hover:bg-secondary text-text"
              }`}
            >
              <div className="flex items-center gap-2">
                <Icon className={`w-4 h-4 ${layer.active ? "text-primary" : "text-text-muted"}`} />
                <span>{layer.label}</span>
              </div>
              
              {/* Toggle switch visual */}
              <div className={`w-7 h-4 rounded-full p-0.5 transition-colors ${layer.active ? "bg-primary" : "bg-border"}`}>
                <div className={`bg-surface w-3 h-3 rounded-full shadow-sm transform transition-transform ${layer.active ? "translate-x-3" : "translate-x-0"}`} />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
