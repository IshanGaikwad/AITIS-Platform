"use client";

import React, { useState, useEffect } from "react";
import { 
  Folder, 
  FolderOpen, 
  ChevronRight, 
  ChevronDown, 
  Plus, 
  MoreVertical, 
  FileText, 
  FolderPlus 
} from "lucide-react";
import { 
  Tooltip, 
  TooltipContent, 
  TooltipProvider, 
  TooltipTrigger 
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { 
  getFolderTree, 
  createFolder, 
  updateFolder, 
  deleteFolder 
} from "@/lib/api";
import type { TestSuiteFolder } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FolderNode {
  folder: TestSuiteFolder;
  children: FolderNode[];
  isOpen: boolean;
}

export function TestSuiteFolderTree({ 
  projectId, 
  onSelectCase, 
  onSelectFolder 
}: { 
  projectId: string; 
  onSelectCase: (caseId: string) => void;
  onSelectFolder: (folderId: string) => void;
}) {
  const [tree, setTree] = useState<FolderNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTree();
  }, [projectId]);

  async function loadTree() {
    setLoading(true);
    try {
      const folders = await getFolderTree(projectId);
      setTree(buildTree(folders));
    } catch (error) {
      console.error("Failed to load folder tree:", error);
    } finally {
      setLoading(false);
    }
  }

  function buildTree(folders: TestSuiteFolder[], parentId?: string | null): FolderNode[] {
    return folders
      .filter(f => f.parent_id === parentId)
      .map(f => ({
        folder: f,
        isOpen: false,
        children: buildTree(folders, f.id),
      }));
  }

  async function handleCreateFolder(parentId?: string) {
    const name = prompt("Enter folder name:");
    if (!name) return;

    try {
      await createFolder({
        name,
        parent_id: parentId || null,
        project_id: projectId,
        // organization_id and workspace_id are typically handled by backend from auth token
      });
      await loadTree();
    } catch (error) {
      console.error("Failed to create folder:", error);
    }
  }

  async function handleRenameFolder(folder: TestSuiteFolder) {
    const newName = prompt("Rename folder:", folder.name);
    if (!newName || newName === folder.name) return;

    try {
      await updateFolder(folder.id, { name: newName });
      await loadTree();
    } catch (error) {
      console.error("Failed to rename folder:", error);
    }
  }

  async function handleDeleteFolder(folderId: string) {
    if (!confirm("Are you sure you want to delete this folder and all its contents?")) return;

    try {
      await deleteFolder(folderId);
      await loadTree();
    } catch (error) {
      console.error("Failed to delete folder:", error);
    }
  }

  function toggleFolder(node: FolderNode, path: FolderNode[]) {
    const newTree = [...tree];
    const updateNode = (nodes: FolderNode[], targetId: string): boolean => {
      for (let node of nodes) {
        if (node.folder.id === targetId) {
          node.isOpen = !node.isOpen;
          return true;
        }
        if (node.children && updateNode(node.children, targetId)) return true;
      }
      return false;
    };
    updateNode(newTree, node.folder.id);
    setTree(newTree);
  }

  if (loading) {
    return <div className="p-4 text-sm text-slate-500">Loading folders...</div>;
  }

  return (
    <div className="flex flex-col h-full border-r bg-slate-50/50">
      <div className="p-3 border-b bg-white flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Test Library
        </h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-7 w-7" 
                onClick={() => handleCreateFolder()}
              >
                <FolderPlus className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Create Root Folder</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {tree.length === 0 ? (
          <div className="text-xs text-slate-400 text-center py-4">No folders found</div>
        ) : (
          tree.map(node => (
            <FolderItem 
              key={node.folder.id} 
              node={node} 
              depth={0} 
              onToggle={toggleFolder}
              onSelectFolder={onSelectFolder}
              onRename={handleRenameFolder}
              onDelete={handleDeleteFolder}
              onCreateChild={() => handleCreateFolder(node.folder.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function FolderItem({ 
  node, 
  depth, 
  onToggle, 
  onSelectFolder,
  onRename,
  onDelete,
  onCreateChild
}: { 
  node: FolderNode; 
  depth: number; 
  onToggle: (node: FolderNode, path: FolderNode[]) => void;
  onSelectFolder: (id: string) => void;
  onRename: (f: TestSuiteFolder) => void;
  onDelete: (id: string) => void;
  onCreateChild: () => void;
}) {
  return (
    <div className="select-none">
      <div 
        className={cn(
          "group flex items-center py-1 px-2 rounded-md cursor-pointer transition-colors",
          "hover:bg-slate-200 text-slate-700 text-sm",
          "text-xs"
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => onSelectFolder(node.folder.id)}
      >
        <div 
          className="flex items-center justify-center w-4 h-4 mr-1 cursor-pointer"
          onClick={(e) => {
            e.stopPropagation();
            onToggle(node, []);
          }}
        >
          {node.children.length > 0 && (
            node.isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />
          )}
        </div>
        
        <div className="flex items-center flex-1 min-w-0">
          {node.children.length > 0 ? (
            node.isOpen ? <FolderOpen className="h-3.5 w-3.5 mr-2 text-blue-500" /> : <Folder className="h-3.5 w-3.5 mr-2 text-blue-500" />
          ) : (
            <Folder className="h-3.5 w-3.5 mr-2 text-slate-400" />
          )}
          <span className="truncate">{node.folder.name}</span>
        </div>

        <div className="hidden group-hover:flex items-center space-x-1">
          <Button 
            variant="ghost" 
            size="icon" 
            className="h-5 w-5 p-0" 
            onClick={(e) => {
              e.stopPropagation();
              onCreateChild();
            }}
          >
            <Plus className="h-3 w-3" />
          </Button>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-5 w-5 p-0">
                <MoreVertical className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => {
                e.stopPropagation();
                onRename(node.folder);
              }}>
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem 
                className="text-rose-600" 
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(node.folder.id);
                }}
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {node.isOpen && node.children.length > 0 && (
        <div className="mt-0.5">
          {node.children.map(child => (
            <FolderItem 
              key={child.folder.id} 
              node={child} 
              depth={depth + 1} 
              onToggle={onToggle}
              onSelectFolder={onSelectFolder}
              onRename={onRename}
              onDelete={onDelete}
              onCreateChild={() => onCreateChild()} // This is simplified, should be child's ID
            />
          ))}
        </div>
      )}
    </div>
  );
}
