import React, { useState } from 'react';
import { Button, Dropdown, Form, Spinner } from 'react-bootstrap';
import { useParams } from 'react-router-dom';
import { useRecoilCallback, useRecoilValue } from 'recoil';
import { createEditor, Node } from 'slate';
import { Slate, Editable, withReact } from 'slate-react';
import { ProtocolBlockEditor } from '../components/ProtocolBlockEditor';
import { labflowOptions } from '../config';
import { BlockDefinition } from '../models/block-definition';
import { Protocol } from '../models/protocol';
import { apiFetch } from '../state/api';
import { auth0State, protocolsState } from '../state/atoms';
import { protocolQuery } from '../state/selectors';
import * as uuid from 'uuid';
import { DragSourceMonitor, DropTargetMonitor, useDrag, useDrop, XYCoord } from 'react-dnd';
import { CheckCircle } from 'react-bootstrap-icons';
import moment from 'moment';

// Define a serializing function that takes a value and returns a string.
export function serializeSlate(value: Node[]): string {
    return (
        value
            // Return the string content of each paragraph in the value's children.
            .map(n => Node.string(n))
            // Join them all with line breaks denoting paragraphs.
            .join('\n')
    )
}

// Define a deserializing function that takes a string and returns a value.
export function deserializeSlate(str: string): Node[] {
    // Return a value array of children derived by splitting the string.
    return str.split('\n').map(line => {
        return {
            children: [{ text: line }],
        }
    })
}

interface DragItem {
    type: 'protocol-block';
    index: number;
}
interface DragResult {
    isDragging: boolean;
}

export function ProtocolDraggableBlock({ index, block, setBlock, moveBlock }: {
    index: number;
    block?: BlockDefinition;
    setBlock: (block?: BlockDefinition) => void;
    moveBlock: (dragIndex: number, hoverIndex: number) => void;
}) {
    const ref = React.useRef<HTMLDivElement>(null);
    const [, drop] = useDrop({
        accept: 'protocol-block',
        hover(item: DragItem, monitor: DropTargetMonitor) {
            if (!ref.current || item.index === index) {
                return;
            }

            const hoverBoundingRect = ref.current.getBoundingClientRect();
            const hoverMiddleY = (hoverBoundingRect.bottom - hoverBoundingRect.top) / 2;
            const clientOffset = monitor.getClientOffset()
            const hoverClientY = (clientOffset as XYCoord).y - hoverBoundingRect.top

            if (item.index < index && hoverClientY < hoverMiddleY) {
                // Dragging downwards
                return
            }
            if (item.index > index && hoverClientY > hoverMiddleY) {
                // Dragging upwards
                return
            }

            // Time to actually perform the action
            moveBlock(item.index, index)
            item.index = index
        },
    });

    const [{ isDragging }, drag] = useDrag<DragItem, unknown, DragResult>({
        item: { type: 'protocol-block', index },
        collect: (monitor: DragSourceMonitor) => ({ isDragging: monitor.isDragging() }),
    });

    const opacity = isDragging ? 0 : 1;
    drag(drop(ref));
    return (
        <div ref={ref} style={{ opacity }} className="mt-5 mb-5">
            <ProtocolBlockEditor index={index} block={block} setBlock={setBlock} />
        </div>
    );
}

export interface ProtocolEditorPageParams {
    id: string;
}

export function ProtocolEditorPage() {
    const [name, setName] = useState<string | null>(null);
    const [description, setDescription] = useState<Node[] | null>(null);
    const [blocks, setBlocks] = useState<BlockDefinition[] | null>(null);
    const [formSaving, setFormSaving] = useState<boolean>(false);
    const [formSavedTime, setFormSavedTime] = useState<string | null>(null);
    const editor = React.useMemo(() => withReact(createEditor()), []);
    const { id } = useParams<ProtocolEditorPageParams>();
    const protocol = useRecoilValue(protocolQuery(parseInt(id)));
    const protocolUpsert = useRecoilCallback(({ set, snapshot }) => async (protocol: Protocol) => {
        setFormSaving(true);
        try {
            const { auth0Client } = await snapshot.getPromise(auth0State);
            const method = protocol.id ? "PUT" : "POST";
            const path = protocol.id ? `protocol/${protocol.id}` : "protocol";
            const created: Protocol = await apiFetch(labflowOptions, () => auth0Client, method, path, protocol);
            set(protocolsState, state => {
                if (created.id) {
                    state.protocolCache.set(created.id, created);
                    return state;
                } else {
                    throw new Error("Received a protocol without an ID from server!");
                }
            });
        } finally {
            setFormSaving(false);
            setFormSavedTime(moment().format());
        }
    });

    const currentName = name || (protocol && protocol.name) || "";
    const currentDescription = description || (protocol && protocol.description && deserializeSlate(protocol.description)) || [{text: ''}];
    const currentBlocks = blocks || (protocol && protocol.blocks) || [];

    const updateBlock = (block?: BlockDefinition) => {
        if (block) {
            setBlocks(currentBlocks.map(b => (b.id === block.id) ? block : b));
        }
    };
    const moveBlock = React.useCallback(
        (dragIndex: number, hoverIndex: number) => {
            const dragBlock = currentBlocks[dragIndex]
            const newBlocks = [...currentBlocks];
            newBlocks.splice(dragIndex, 1);
            newBlocks.splice(hoverIndex, 0, dragBlock);
            setBlocks(newBlocks);
        },
        [currentBlocks],
    )

    return (
        <Form className="mt-4">
            <Form.Group controlId="formProtocolTitle">
                <Form.Label>Protocol Title</Form.Label>
                <Form.Control
                    type="text"
                    value={currentName}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName((e.target as HTMLInputElement).value)}
                />
            </Form.Group>
            <Form.Group>
                <Form.Label>Description</Form.Label>
                <Slate
                    editor={editor}
                    value={currentDescription}
                    onChange={setDescription}
                >
                    <Editable />
                </Slate>
            </Form.Group>

            {currentBlocks.map((block, index) => {
                if (!block || !block.id) {
                    return undefined;
                }
                return <ProtocolDraggableBlock
                    key={block.id}
                    index={index}
                    moveBlock={moveBlock}
                    block={block}
                    setBlock={updateBlock}
                />;
            })}

            <div className="row">
                <Dropdown className="col-auto">
                    <Dropdown.Toggle variant="success" id="block-add">
                        Add a new section
                    </Dropdown.Toggle>

                    <Dropdown.Menu>
                        <Dropdown.Item onClick={() => setBlocks([...currentBlocks, { id: uuid.v4(), type: 'text-question' }])}>Text Question</Dropdown.Item>
                        <Dropdown.Item onClick={() => setBlocks([...currentBlocks, { id: uuid.v4(), type: 'options-question' }])}>Options Question</Dropdown.Item>
                        <Dropdown.Item onClick={() => setBlocks([...currentBlocks, { id: uuid.v4(), type: 'plate-sampler' }])}>Run Plate Sampler</Dropdown.Item>
                        <Dropdown.Item onClick={() => setBlocks([...currentBlocks, { id: uuid.v4(), type: 'plate-add-reagent' }])}>Add Reagent to Plate</Dropdown.Item>
                        <Dropdown.Item onClick={() => setBlocks([...currentBlocks, { id: uuid.v4(), type: 'plate-sequencer' }])}>Run Plate Sequencer</Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
                <Button
                    className="col-auto ml-3"
                    variant="primary"
                    onClick={() => protocolUpsert({
                        id: parseInt(id),
                        name: currentName,
                        description: serializeSlate(currentDescription),
                        blocks: currentBlocks,
                    })}
                    disabled={formSaving}
                >
                    {
                        formSaving
                            ? <><Spinner size="sm" animation="border" /> Saving...</>
                            : <>Save</>
                    }
                </Button>
                <div className="col"></div>
                <div className="col-auto my-auto">
                    { formSavedTime && <><CheckCircle /> Last saved on: {moment(formSavedTime).format('LLLL')}</> }
                </div>
            </div>
        </Form>
    );
}
