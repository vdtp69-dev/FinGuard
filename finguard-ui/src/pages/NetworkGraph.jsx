import { useEffect, useRef, useState } from 'react';
import { getGraphData } from '../api';
import * as d3 from 'd3';
import { Network, Search, AlertCircle, Share2, ZoomIn, ZoomOut, Maximize } from 'lucide-react';

const COLORS = { 1: '#58a6ff', 2: '#bc8cff', 3: '#ffa657' };

export default function NetworkGraph() {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [data, setData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getGraphData().then(d => {
      setData(d);
      setLoading(false);
    }).catch(e => {
      console.error(e);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!data || !data.nodes || !data.links || !svgRef.current || !containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const g = svg.append("g");

    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoom);

    svg.call(zoom.transform, d3.zoomIdentity.translate(width/2, height/2).scale(0.8));

    // D3 expects `source`/`target`, but backend graph JSON may use `from`/`to`.
    const links = data.links.map(l => ({
      ...l,
      source: l.source ?? l.from,
      target: l.target ?? l.to,
    }));

    // Simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("x", d3.forceX())
      .force("y", d3.forceY());

    // Edges
    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", d => d.has_fraud ? "#f85149" : "#21262d")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", d => Math.sqrt(d.weight || 1));

    // Nodes
    const node = g.append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .call(drag(simulation));

    // Outer ring for fraud nodes
    node.filter(d => d.type === "user" && d.fraud_ring_candidate)
      .append("circle")
      .attr("r", d => (d.centrality * 100) + 12)
      .attr("fill", "none")
      .attr("stroke", "#f85149")
      .attr("stroke-width", 2)
      .attr("class", "animate-ping opacity-75");

    // Main circle
    node.append("circle")
      .attr("r", d => d.type === "user" ? (d.centrality * 100) + 8 : 6)
      .attr("fill", d => d.type === "user" ? (COLORS[d.id] || "#e6edf3") : (d.fraud_rate > 0.5 ? "#f85149" : d.fraud_rate > 0.1 ? "#f0883e" : "#8b949e"))
      .attr("cursor", "pointer")
      .on("click", (e, d) => setSelectedNode(Object.assign({}, d)));

    // Labels
    node.append("text")
      .text(d => d.label || d.id)
      .attr("x", 12)
      .attr("y", 4)
      .attr("fill", "#8b949e")
      .style("font-size", "10px")
      .style("pointer-events", "none");

    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      node
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    function drag(sim) {
      return d3.drag()
        .on("start", (e) => {
          if (!e.active) sim.alphaTarget(0.3).restart();
          e.subject.fx = e.subject.x;
          e.subject.fy = e.subject.y;
        })
        .on("drag", (e) => {
          e.subject.fx = e.x;
          e.subject.fy = e.y;
        })
        .on("end", (e) => {
          if (!e.active) sim.alphaTarget(0);
          e.subject.fx = null;
          e.subject.fy = null;
        });
    }

  }, [data]);

  const handleZoom = (scale) => {
    if (!svgRef.current) return;
    d3.select(svgRef.current).transition().call(d3.zoom().scaleBy, scale);
  };

  if (loading) return <div className="p-8 text-secondary">Loading neural topology...</div>;

  return (
    <div className="flex flex-col h-[85vh] space-y-4">
      <div className="flex justify-between items-center border-b border-border pb-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2"><Network className="text-primary"/> Network Topology</h1>
          <p className="text-secondary mt-1 tracking-wider uppercase text-xs">Betweenness Centrality & Global Exposure Map</p>
          <p className="text-secondary text-xs mt-2 leading-relaxed">
            This is a force-directed D3 layout: nodes are connected entities and the graph positions itself based on link connectivity.
            User nodes scale with <span className="text-primary font-semibold">centrality</span>, edge thickness reflects <span className="text-primary font-semibold">weight</span>, and color indicates fraud likelihood.
            Click a node to drill into its exposure metrics.
          </p>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-4 gap-4">
        <div className="col-span-3 card-finguard p-0 overflow-hidden relative" ref={containerRef}>
          <div className="absolute top-4 right-4 flex gap-2 z-10">
            <button onClick={() => handleZoom(1.5)} className="p-2 bg-surface border border-border rounded-lg text-secondary hover:text-primary"><ZoomIn className="w-4 h-4" /></button>
            <button onClick={() => handleZoom(0.5)} className="p-2 bg-surface border border-border rounded-lg text-secondary hover:text-primary"><ZoomOut className="w-4 h-4" /></button>
            <button onClick={() => d3.select(svgRef.current).transition().call(d3.zoom().transform, d3.zoomIdentity.translate(containerRef.current.clientWidth/2, containerRef.current.clientHeight/2).scale(0.8))} className="p-2 bg-surface border border-border rounded-lg text-secondary hover:text-primary"><Maximize className="w-4 h-4" /></button>
          </div>
          <svg className="w-full h-full cursor-move" ref={svgRef}></svg>
        </div>

        <div className="col-span-1 space-y-4 overflow-y-auto pr-2">
          {selectedNode ? (
            <div className="card-finguard animate-in slide-in-from-right-2">
              <h2 className="text-lg font-bold border-b border-border pb-2 mb-3 truncate flex items-center gap-2">
                 <Search className="w-4 h-4 text-user-aman" /> {selectedNode.label || selectedNode.id}
              </h2>
              <div className="space-y-3 text-sm">
                <div><span className="text-secondary uppercase text-xs block">Entity Class</span> <span className="capitalize">{selectedNode.type}</span></div>
                {selectedNode.type === "user" ? (
                  <>
                    <div><span className="text-secondary uppercase text-xs block">Centrality Power</span> {(selectedNode.centrality * 100).toFixed(1)}%</div>
                    <div><span className="text-secondary uppercase text-xs block">Total Vectors</span> {selectedNode.total_txns}</div>
                    {selectedNode.fraud_ring_candidate && (
                      <div className="mt-4 bg-decision-block/10 text-decision-block p-2 rounded border border-decision-block/30 flex items-center gap-2 text-xs font-bold uppercase">
                        <AlertCircle className="w-4 h-4" /> Detected Ring Target
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div><span className="text-secondary uppercase text-xs block">Global Fraud Ratio</span> {(selectedNode.fraud_rate * 100).toFixed(1)}%</div>
                    <div><span className="text-secondary uppercase text-xs block">Linked Edges</span> {selectedNode.total_txns}</div>
                  </>
                )}
              </div>
              <button onClick={() => setSelectedNode(null)} className="w-full mt-6 py-2 border border-border text-secondary text-xs rounded hover:bg-surface">Clear Selection</button>
            </div>
          ) : (
            <div className="card-finguard text-center text-secondary py-12">
              <Share2 className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p className="text-sm">Click any <span className="text-[#58a6ff]">node</span> on the graph to drill down into entity exposure vectors.</p>
            </div>
          )}

          {data?.fraud_ring_candidates?.length > 0 && (
            <div className="card-finguard border-t-2 border-t-decision-block">
              <h3 className="text-sm font-bold border-b border-border pb-2 mb-3">Ring Targets</h3>
              <div className="space-y-2">
                {data.fraud_ring_candidates.map(u => (
                  <div key={u} className="text-xs flex justify-between">
                    <span className="text-secondary">User {u}</span>
                    <span className="text-decision-block font-bold">Investigate</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
