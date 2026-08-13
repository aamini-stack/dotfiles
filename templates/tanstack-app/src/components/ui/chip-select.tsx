import { CheckIcon } from '@phosphor-icons/react'
import type { ElementType } from 'react'

import { cn } from '@/lib/utils/ui'

type ChipSelectOption<TValue extends string = string> = {
	value: TValue
	label: string
	icon?: ElementType
}

type ChipSelectProps<TValue extends string = string> = {
	options: ChipSelectOption<TValue>[]
	selected: TValue[]
	onChange: (selected: TValue[]) => void
	maxSelections?: number | undefined
	disabled?: boolean
	className?: string
}

export function ChipSelect<TValue extends string>({
	options,
	selected,
	onChange,
	maxSelections,
	disabled = false,
	className,
}: ChipSelectProps<TValue>) {
	const toggle = (value: TValue) => {
		if (disabled) return
		const isSelected = selected.includes(value)
		if (isSelected) {
			onChange(selected.filter((v) => v !== value))
			return
		}
		if (maxSelections && selected.length >= maxSelections) {
			return
		}
		onChange([...selected, value])
	}

	return (
		<div
			className={cn(
				'grid grid-cols-1 gap-2 min-[480px]:grid-cols-2',
				className,
			)}
		>
			{options.map((option) => {
				const isSelected = selected.includes(option.value)
				const isAtLimit =
					!isSelected &&
					maxSelections !== undefined &&
					selected.length >= maxSelections

				return (
					<button
						key={option.value}
						type="button"
						disabled={isAtLimit || disabled}
						onClick={() => toggle(option.value)}
						aria-pressed={isSelected}
						className={cn(
							'flex min-h-10 items-center gap-2.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-all',
							isSelected
								? 'border-primary bg-sky-tint text-primary'
								: 'border-border bg-background text-foreground hover:border-foreground/30 hover:bg-muted/30',
							(isAtLimit || disabled) && 'pointer-events-none opacity-50',
						)}
					>
						<span
							className={cn(
								'flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border transition-colors',
								isSelected
									? 'border-primary bg-primary text-primary-foreground'
									: 'border-muted-foreground/40 bg-background',
							)}
						>
							{isSelected ? (
								<CheckIcon className="h-3 w-3" weight="bold" />
							) : null}
						</span>
						{option.icon ? (
							<option.icon className="h-4 w-4 shrink-0" weight="duotone" />
						) : null}
						{option.label}
					</button>
				)
			})}
		</div>
	)
}
