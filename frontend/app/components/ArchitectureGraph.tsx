"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { GraphNode, GraphEdge, KnowledgeGraph } from "../types";

type SceneNode = GraphNode & {
  x: number;
  y: number;
  z: number;
};

const visibleTypes = new Set(["module", "file", "function", "class", "source", "claim"]);
const edgeTypes = new Set(["contains", "imports", "documents", "exemplifies", "related"]);

export function ArchitectureGraph({
  graph,
  selectedNodeId,
  onSelectNode,
}: {
  graph: KnowledgeGraph;
  selectedNodeId?: string;
  onSelectNode: (node: GraphNode) => void | Promise<void>;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const nodesRef = useRef<SceneNode[]>([]);
  const [hovered, setHovered] = useState<SceneNode | null>(null);
  const [webglUnavailable, setWebGLUnavailable] = useState(false);

  const sceneNodes = useMemo(() => layoutNodes(selectSceneNodes(graph.nodes || [], graph.edges || [])), [graph.edges, graph.nodes]);
  const sceneEdges = useMemo(() => {
    const ids = new Set(sceneNodes.map((node) => node.id));
    return (graph.edges || []).filter((edge) => ids.has(edge.source) && ids.has(edge.target) && edgeTypes.has(edge.type)).slice(0, 260);
  }, [graph.edges, sceneNodes]);

  useEffect(() => {
    nodesRef.current = sceneNodes;
  }, [sceneNodes]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    if (!canUseWebGL()) {
      setWebGLUnavailable(true);
      return;
    }

    const width = mount.clientWidth || 720;
    const height = mount.clientHeight || 500;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    mount.innerHTML = "";
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 3000);
    camera.position.set(0, 0, 720);

    const nodeGroup = new THREE.Group();
    const edgeGroup = new THREE.Group();
    scene.add(edgeGroup);
    scene.add(nodeGroup);

    const nodeById = new Map(sceneNodes.map((node) => [node.id, node]));
    for (const edge of sceneEdges) {
      const source = nodeById.get(edge.source);
      const target = nodeById.get(edge.target);
      if (!source || !target) continue;
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(source.x, source.y, source.z),
        new THREE.Vector3(target.x, target.y, target.z),
      ]);
      const material = new THREE.LineBasicMaterial({ color: edgeColor(edge.type), transparent: true, opacity: 0.42 });
      edgeGroup.add(new THREE.Line(geometry, material));
    }

    const meshes: THREE.Mesh[] = [];
    for (const node of sceneNodes) {
      const geometry = new THREE.SphereGeometry(node.type === "module" ? 7 : 5, 20, 20);
      const material = new THREE.MeshBasicMaterial({ color: nodeColor(node.type) });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(node.x, node.y, node.z);
      mesh.userData.nodeId = node.id;
      nodeGroup.add(mesh);
      meshes.push(mesh);
    }

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let frame = 0;
    let disposed = false;

    function updatePointer(event: PointerEvent) {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    }

    function pick(event: PointerEvent, shouldSelect: boolean) {
      updatePointer(event);
      raycaster.setFromCamera(pointer, camera);
      const match = raycaster.intersectObjects(meshes)[0]?.object as THREE.Mesh | undefined;
      const node = match ? sceneNodes.find((item) => item.id === match.userData.nodeId) || null : null;
      setHovered(node);
      if (shouldSelect && node) onSelectNode(node);
    }

    function resize() {
      const target = mountRef.current;
      if (!target) return;
      const nextWidth = target.clientWidth || width;
      const nextHeight = target.clientHeight || height;
      renderer.setSize(nextWidth, nextHeight);
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
    }

    renderer.domElement.addEventListener("pointermove", (event) => pick(event, false));
    renderer.domElement.addEventListener("click", (event) => pick(event, true));
    window.addEventListener("resize", resize);

    function animate() {
      if (disposed) return;
      frame += 0.006;
      nodeGroup.rotation.y = frame;
      edgeGroup.rotation.y = frame;
      for (const mesh of meshes) {
        const isSelected = mesh.userData.nodeId === selectedNodeId;
        mesh.scale.setScalar(isSelected ? 1.7 : 1);
      }
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }
    animate();

    return () => {
      disposed = true;
      window.removeEventListener("resize", resize);
      renderer.dispose();
      for (const mesh of meshes) {
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      }
      mount.innerHTML = "";
    };
  }, [onSelectNode, sceneEdges, sceneNodes, selectedNodeId]);

  return (
    <section className="flex flex-col h-full bg-slate-900 text-slate-100 relative p-6 space-y-4" aria-label="Architecture relationship map">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 shrink-0">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white font-display">Architecture Map</h2>
          <p className="text-xs text-slate-400 mt-1">{sceneNodes.length} nodes · {sceneEdges.length} relationships from the current graph.</p>
        </div>
        <div className="text-xs font-mono px-3 py-1 bg-slate-800 border border-slate-700 rounded text-slate-300">
          {hovered ? (hovered.metadata?.path || hovered.name) : "Click a node to inspect evidence"}
        </div>
      </div>
      {webglUnavailable ? (
        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm border border-slate-800 rounded-lg bg-slate-950">
          WebGL unavailable. Use the Files and Graph lists to inspect relationships.
        </div>
      ) : (
        <div className="flex-1 w-full bg-slate-950 border border-slate-800 rounded-lg relative overflow-hidden" ref={mountRef} />
      )}
    </section>
  );
}

function layoutNodes(nodes: GraphNode[]): SceneNode[] {
  const byType = new Map<string, GraphNode[]>();
  for (const node of nodes) {
    byType.set(node.type, [...(byType.get(node.type) || []), node]);
  }
  const ordered = [...byType.entries()].sort(([left], [right]) => left.localeCompare(right));
  const result: SceneNode[] = [];
  ordered.forEach(([type, items], ringIndex) => {
    const radius = 70 + ringIndex * 42;
    items.forEach((node, index) => {
      const angle = (index / Math.max(1, items.length)) * Math.PI * 2 + ringIndex * 0.45;
      result.push({
        ...node,
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        z: (ringIndex - ordered.length / 2) * 34 + (type === "source" || type === "claim" ? 80 : 0),
      });
    });
  });
  return result;
}

function selectSceneNodes(nodes: GraphNode[], edges: GraphEdge[]) {
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const selectedIds = new Set<string>();
  for (const edge of edges) {
    if (!edgeTypes.has(edge.type)) continue;
    const source = nodeById.get(edge.source);
    const target = nodeById.get(edge.target);
    if (!source || !target || !visibleTypes.has(source.type) || !visibleTypes.has(target.type)) continue;
    if (selectedIds.size + 2 > 140) break;
    selectedIds.add(edge.source);
    selectedIds.add(edge.target);
  }
  const priority = new Map([
    ["module", 0],
    ["file", 1],
    ["function", 2],
    ["class", 3],
    ["source", 4],
    ["claim", 5],
  ]);
  return nodes
    .filter((node) => visibleTypes.has(node.type))
    .filter((node) => selectedIds.has(node.id))
    .sort((left, right) => {
      const priorityDelta = (priority.get(left.type) ?? 99) - (priority.get(right.type) ?? 99);
      if (priorityDelta !== 0) return priorityDelta;
      const leftPath = left.metadata?.path || left.name;
      const rightPath = right.metadata?.path || right.name;
      return leftPath.localeCompare(rightPath);
    })
    .slice(0, 140);
}

function canUseWebGL() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl") || canvas.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

function nodeColor(type: string) {
  if (type === "source") return 0x1f8a4c;
  if (type === "claim") return 0xb5790a;
  if (type === "module") return 0x2453e0;
  if (type === "function" || type === "class") return 0x5b6472;
  return 0x8a93a3;
}

function edgeColor(type: string) {
  if (type === "documents" || type === "exemplifies") return 0x1f8a4c;
  if (type === "imports") return 0xb5790a;
  return 0x2453e0;
}
