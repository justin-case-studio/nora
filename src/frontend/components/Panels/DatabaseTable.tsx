import React, { useState, useEffect } from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  HStack,
  Input,
  Text,
  Box,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  flexRender,
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  ColumnDef,
  RowData,
  SortingState,
} from '@tanstack/react-table';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';

export interface FileRecord {
  id: number;
  file_path: string;
  file_name: string;
  size: number;
  modified_date: string;
  sha256: string;
  tx_id: string;
  registered_at: string;
  user_notes?: string;
}

declare module '@tanstack/react-table' {
  interface TableMeta<TData extends RowData> {
    updateData: (rowIndex: number, columnId: string, value: string) => void;
  }
}

const EditableCell: React.FC<any> = ({ getValue, row, column, table }) => {
  const initialValue = getValue() || '';
  const [value, setValue] = useState(initialValue);
  const { updateData } = table.options.meta;
  const inputRef = React.useRef<HTMLInputElement>(null);

  const onBlur = () => {
    if (value !== initialValue) {
      updateData(row.index, column.id, value);
    }
  };

  // Add keydown handler to save on Enter and cancel on Escape
  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      inputRef.current?.blur(); // Trigger onBlur to save
    } else if (e.key === 'Escape') {
      setValue(initialValue); // Revert to original value
      inputRef.current?.blur(); // And blur the input
    }
  };

  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  return (
    <Input
      ref={inputRef}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={onBlur}
      onKeyDown={onKeyDown}
      variant="filled"
      size="sm"
      w="100%"
      placeholder="Add a note..."
    />
  );
};

export const defaultColumn: Partial<ColumnDef<FileRecord>> = {
  cell: ({ getValue }) => <Text>{getValue() as string}</Text>,
};

export { EditableCell };

interface DatabaseTableProps {
  data: FileRecord[];
  columns: ColumnDef<FileRecord>[];
  globalFilter: string;
  setGlobalFilter: (filter: string) => void;
  sorting: SortingState;
  setSorting: React.Dispatch<React.SetStateAction<SortingState>>;
  updateData: (rowIndex: number, columnId: string, value: string) => void;
}

export const DatabaseTable: React.FC<DatabaseTableProps> = ({
  data,
  columns,
  globalFilter,
  setGlobalFilter,
  sorting,
  setSorting,
  updateData,
}) => {
  const rowHoverBg = useColorModeValue('gray.100', 'gray.700');
  
  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    meta: {
      updateData,
    },
  });

  // Handler for copy event - replace truncated text with full value for tx_id/sha256
  const handleCellCopy = async (e: React.ClipboardEvent<HTMLTableCellElement>, cell: any) => {
    const columnId = cell.column.id;
    if (columnId === 'tx_id' || columnId === 'sha256') {
      try {
        const rawValue = cell.getValue();
        if (rawValue !== null && rawValue !== undefined) {
          e.preventDefault();
          await navigator.clipboard.writeText(String(rawValue));
        }
      } catch (error) {
        console.error('Failed to copy full value to clipboard:', error);
        // Let the default copy behavior proceed
      }
    }
  };

  // Handler for double-click to select cell text
  const handleCellDoubleClick = async (e: React.MouseEvent<HTMLTableCellElement>, cell: any) => {
    // Don't select if clicking on interactive elements (buttons, inputs, etc.)
    const target = e.target as HTMLElement;
    if (target.tagName === 'BUTTON' || 
        target.tagName === 'INPUT' || 
        target.closest('button') || 
        target.closest('input') ||
        target.closest('[role="button"]') ||
        target.closest('[role="menu"]')) {
      return;
    }

    // Don't select for the Actions column
    if (cell.column.id === 'actions') {
      return;
    }

    // For tx_id and sha256 columns, copy the full raw value to clipboard
    const columnId = cell.column.id;
    if (columnId === 'tx_id' || columnId === 'sha256') {
      try {
        const rawValue = cell.getValue();
        if (rawValue !== null && rawValue !== undefined) {
          await navigator.clipboard.writeText(String(rawValue));
          // Visual feedback: briefly select the cell text
          const cellElement = e.currentTarget;
          const range = document.createRange();
          const selection = window.getSelection();
          if (selection && cellElement.textContent) {
            selection.removeAllRanges();
            range.selectNodeContents(cellElement);
            selection.addRange(range);
            // Clear selection after a brief moment
            setTimeout(() => {
              if (selection.rangeCount > 0) {
                selection.removeAllRanges();
              }
            }, 200);
          }
          return;
        }
      } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        // Fall through to text selection
      }
    }

    // Default: Select the visible text content of the cell
    const cellElement = e.currentTarget;
    const range = document.createRange();
    const selection = window.getSelection();
    
    if (!selection || !cellElement.textContent) {
      return;
    }

    selection.removeAllRanges();
    
    // Try to select text nodes, excluding interactive elements
    const walker = document.createTreeWalker(
      cellElement,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          // Skip text nodes that are inside buttons, inputs, or menus
          let parent = node.parentElement;
          while (parent && parent !== cellElement) {
            if (parent.tagName === 'BUTTON' || 
                parent.tagName === 'INPUT' ||
                parent.closest('button') ||
                parent.closest('input') ||
                parent.closest('[role="button"]') ||
                parent.closest('[role="menu"]')) {
              return NodeFilter.FILTER_REJECT;
            }
            parent = parent.parentElement;
          }
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );
    
    let firstNode: Node | null = null;
    let lastNode: Node | null = null;
    let textNode = walker.nextNode();
    
    while (textNode) {
      if (!firstNode) firstNode = textNode;
      lastNode = textNode;
      textNode = walker.nextNode();
    }
    
    if (firstNode && lastNode) {
      range.setStart(firstNode, 0);
      range.setEnd(lastNode, lastNode.textContent?.length || 0);
      selection.addRange(range);
    } else {
      // Fallback: select all text content (excluding interactive elements)
      range.selectNodeContents(cellElement);
      selection.addRange(range);
    }
  };

  return (
    <Box borderWidth="1px" borderRadius="lg" overflowX="auto" style={{ userSelect: 'text' }}>
      <Table variant="simple" style={{ userSelect: 'text' }}>
        <Thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <Tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <Th key={header.id} colSpan={header.colSpan} userSelect="none" style={{width: header.getSize() !== 150 ? header.getSize() : undefined}}>
                  {header.isPlaceholder ? null : (
                    <HStack
                      spacing={2}
                      cursor={header.column.getCanSort() ? 'pointer' : 'default'}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <Text>
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                      </Text>
                      <Box>
                        {{
                          asc: <FiChevronUp />,
                          desc: <FiChevronDown />,
                        }[header.column.getIsSorted() as string] ?? null}
                      </Box>
                    </HStack>
                  )}
                </Th>
              ))}
            </Tr>
          ))}
        </Thead>
        <Tbody>
          {table.getRowModel().rows.map((row) => (
            <Tr 
              key={row.id} 
              _hover={{ bg: rowHoverBg }}
              style={{ userSelect: 'text' }}
            >
              {row.getVisibleCells().map((cell) => (
                <Td 
                  key={cell.id} 
                  style={{
                    width: cell.column.getSize() !== 150 ? cell.column.getSize() : undefined,
                    userSelect: 'text',
                    WebkitUserSelect: 'text',
                    MozUserSelect: 'text',
                    msUserSelect: 'text'
                  }}
                  onDoubleClick={(e) => handleCellDoubleClick(e, cell)}
                  onCopy={(e) => handleCellCopy(e, cell)}
                  cursor="text"
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </Td>
              ))}
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};