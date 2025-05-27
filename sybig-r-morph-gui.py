        # Create scrollable frame for syllables
        self.syllable_canvas = tk.Canvas(syllable_container)
        scrollbar = ttk.Scrollbar(syllable_container, orient="vertical", command=self.syllable_canvas.yview)
        self.syllable_scrollable_frame = ttk.Frame(self.syllable_canvas)
        
        self.syllable_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.syllable_canvas.configure(scrollregion=self.syllable_canvas.bbox("all"))
        )
        
        self.syllable_canvas.create_window((0, 0), window=self.syllable_scrollable_frame, anchor="nw")
        self.syllable_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.syllable_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.syllable_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.syllable_canvas.bind("<MouseWheel>", _on_mousewheel)
        
    def setup_stress_tab(self, parent):
        # Instructions
        instructions = ttk.Label(parent, text="Apply stress marks to Greek pseudowords:", 
                                font=('TkDefaultFont', 10, 'bold'))
        instructions.pack(anchor=tk.W, pady=(0, 10))
        
        # Input section
        input_frame = ttk.LabelFrame(parent, text="Input Words", padding="10")
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(input_frame, text="Greek Words (one per line):").pack(anchor=tk.W)
        self.stress_input = scrolledtext.ScrolledText(input_frame, height=8, wrap=tk.WORD)
        self.stress_input.pack(fill=tk.BOTH, expand=True, pady=5)
        self.stress_input.bind('<KeyRelease>', self.check_stress_button_state)
        
        # Import and Greek rules buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.import_words_btn = ttk.Button(button_frame, text="Import Generated Words", 
                                          command=self.import_generated_words, state="disabled")
        self.import_words_btn.pack(side=tk.LEFT, padx=5)
        
        self.apply_greek_rules_btn = ttk.Button(button_frame, text="Apply Greek Stress Rules", 
                                               command=self.apply_greek_stress_rules, state="disabled")
        self.apply_greek_rules_btn.pack(side=tk.LEFT, padx=5)
        
        # Stress options section (for manual stress application)
        options_frame = ttk.LabelFrame(parent, text="Manual Stress Options", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(options_frame, text="Select stress position(s):").pack(anchor=tk.W)
        
        # Checkboxes for stress positions
        checkbox_frame = ttk.Frame(options_frame)
        checkbox_frame.pack(fill=tk.X, pady=5)
        
        self.stress_antepenult = tk.BooleanVar()
        self.stress_penult = tk.BooleanVar()
        self.stress_ultima = tk.BooleanVar()
        
        ttk.Checkbutton(checkbox_frame, text="Antepenult (APU) - third to last syllable", 
                       variable=self.stress_antepenult, command=self.check_stress_button_state).pack(anchor=tk.W)
        ttk.Checkbutton(checkbox_frame, text="Penult (PU) - second to last syllable", 
                       variable=self.stress_penult, command=self.check_stress_button_state).pack(anchor=tk.W)
        ttk.Checkbutton(checkbox_frame, text="Ultima (U) - last syllable", 
                       variable=self.stress_ultima, command=self.check_stress_button_state).pack(anchor=tk.W)
        
        help_text = ttk.Label(options_frame, 
                             text="Note: Multiple selections will be distributed evenly across words.",
                             font=('TkDefaultFont', 8))
        help_text.pack(anchor=tk.W, pady=5)
        
        # Action buttons
        action_button_frame = ttk.Frame(options_frame)
        action_button_frame.pack(fill=tk.X, pady=5)
        
        self.apply_stress_btn = ttk.Button(action_button_frame, text="Apply Manual Stress", 
                                          command=self.apply_stress, state="disabled")
        self.apply_stress_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_button_frame, text="Clear", command=self.clear_stress).pack(side=tk.LEFT, padx=5)
        
        # Output section
        output_frame = ttk.LabelFrame(parent, text="Stressed Words", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(output_frame, text="Stressed Words:").pack(anchor=tk.W)
        self.stress_output = scrolledtext.ScrolledText(output_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.stress_output.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Export buttons
        export_frame = ttk.Frame(output_frame)
        export_frame.pack(fill=tk.X, pady=5)
        
        self.copy_stressed_btn = ttk.Button(export_frame, text="Copy Stressed Words", 
                                           command=self.copy_stressed_words, state="disabled")
        self.copy_stressed_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_stressed_btn = ttk.Button(export_frame, text="Save Stressed Words", 
                                           command=self.save_stressed_words, state="disabled")
        self.save_stressed_btn.pack(side=tk.LEFT, padx=5)
        
    def browse_file(self, string_var):
        file_path = filedialog.askopenfilename()
        if file_path:
            string_var.set(file_path)
            
    def update_status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def load_lexicons(self):
        self.update_status("Loading lexicons... (this may take a moment)")
        
        def load_thread():
            try:
                self.available_pos = self.generator.load_lexicons(
                    self.greeklex_path.get(), 
                    self.all_num_clean_path.get()
                )
                
                # Update UI in main thread
                self.root.after(0, self.update_pos_combobox)
                
            except Exception as e:
                error_msg = f"Error loading lexicons: {str(e)}"
                self.root.after(0, lambda: self.update_status(error_msg))
        
        # Start loading thread
        threading.Thread(target=load_thread, daemon=True).start()
        
    def update_pos_combobox(self):
        # Filter to only include desired POS types
        allowed_pos = ["noun", "verb", "adj", "adv", "prep"]
        filtered_pos = [pos for pos in self.available_pos if pos in allowed_pos]
        
        # Add "All" option at the beginning
        pos_options = ["all"] + filtered_pos
        
        self.postype['values'] = pos_options
        self.postype.set("all" if pos_options else "")
        self.postype['state'] = 'readonly'
        self.generate_button['state'] = 'normal'
        self.update_status(f"Lexicons loaded successfully! Found {len(self.available_pos)} parts of speech.")
        
    def on_param_change(self, event=None):
        """Called when generation parameters change to invalidate syllable cache"""
        # Clear syllable selection when parameters change
        self.available_last_syllables = []
        self.selected_last_syllables = []
        self.update_syllable_status()
        
    def load_syllables(self):
        """Load available last syllables based on current parameters"""
        if not hasattr(self.generator, 'lexicons') or not self.generator.lexicons:
            self.update_status("ERROR: Please load lexicons first.")
            return
            
        # Get current parameters
        postype = self.postype.get()
        num_syllables = self.num_syllables.get()
        freq_threshold = self.freq_threshold.get()
        
        if not postype:
            self.update_status("ERROR: Please select a part of speech.")
            return
            
        # If postype is "all", use "noun" as representative for syllable loading
        syllable_postype = "noun" if postype == "all" else postype
        
        self.update_status(f"Loading syllables for {syllable_postype}, {num_syllables} syllables...")
        
        def load_syllables_thread():
            try:
                # Create a status callback for threading
                status_queue = queue.Queue()
                
                def status_callback(message):
                    status_queue.put(message)
                
                # Get syllable dictionary
                syldict = self.generator.get_syllable_dict(
                    postype=syllable_postype,
                    num_syllables=num_syllables,
                    freq_threshold=freq_threshold,
                    status_callback=status_callback
                )
                
                # Process status messages
                while not status_queue.empty():
                    message = status_queue.get()
                    self.root.after(0, lambda m=message: self.update_status(m))
                
                if syldict:
                    # Get last syllables (position = num_syllables)
                    last_syllables = list(syldict[num_syllables])
                    
                    # Update in main thread
                    self.root.after(0, lambda: self.update_available_syllables(last_syllables))
                else:
                    self.root.after(0, lambda: self.update_status("ERROR: Could not load syllables"))
                    
            except Exception as e:
                error_msg = f"Error loading syllables: {str(e)}"
                self.root.after(0, lambda: self.update_status(error_msg))
        
        # Start loading thread
        threading.Thread(target=load_syllables_thread, daemon=True).start()
        
    def update_available_syllables(self, syllables):
        """Update the available syllables and render them"""
        self.available_last_syllables = sorted(syllables)
        # Initially select all syllables
        self.selected_last_syllables = self.available_last_syllables.copy()
        
        self.update_status(f"Loaded {len(self.available_last_syllables)} available last syllables")
        self.update_syllable_status()
        self.render_syllables()
        
    def update_syllable_status(self):
        """Update the syllable selection status displays"""
        if not self.available_last_syllables:
            status_text = "No syllables loaded"
            main_status_text = "No syllables selected"
        elif len(self.selected_last_syllables) == 0:
            status_text = f"0 of {len(self.available_last_syllables)} syllables selected"
            main_status_text = "No syllables selected"
        elif len(self.selected_last_syllables) == len(self.available_last_syllables):
            status_text = "All syllables selected"
            main_status_text = "All syllables selected"
        else:
            status_text = f"{len(self.selected_last_syllables)} of {len(self.available_last_syllables)} syllables selected"
            main_status_text = f"{len(self.selected_last_syllables)} syllables selected"
            
        self.syllable_count_label.config(text=status_text)
        self.syllable_status_label.config(text=main_status_text)
        
    def render_syllables(self):
        """Render syllable checkboxes"""
        # Clear existing syllables
        for widget in self.syllable_scrollable_frame.winfo_children():
            widget.destroy()
            
        if not self.available_last_syllables:
            ttk.Label(self.syllable_scrollable_frame, text="No syllables available. Click 'Load Available Syllables' first.").pack()
            return
            
        # Get search term
        search_term = self.search_var.get().lower()
        
        # Filter syllables based on search
        filtered_syllables = [syl for syl in self.available_last_syllables 
                             if search_term in syl.lower()]
        
        if not filtered_syllables:
            ttk.Label(self.syllable_scrollable_frame, text="No syllables match your search").pack()
            return
            
        # Create checkboxes for filtered syllables
        self.syllable_vars = {}
        
        # Arrange in columns
        columns = 4
        for i, syllable in enumerate(filtered_syllables):
            row = i // columns
            col = i % columns
            
            var = tk.BooleanVar()
            var.set(syllable in self.selected_last_syllables)
            self.syllable_vars[syllable] = var
            
            # Create checkbox
            checkbox = ttk.Checkbutton(
                self.syllable_scrollable_frame, 
                text=syllable, 
                variable=var,
                command=lambda s=syllable: self.toggle_syllable(s)
            )
            checkbox.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            
    def filter_syllables(self, *args):
        """Filter syllables based on search term"""
        self.render_syllables()
        
    def toggle_syllable(self, syllable):
        """Toggle syllable selection"""
        if self.syllable_vars[syllable].get():
            if syllable not in self.selected_last_syllables:
                self.selected_last_syllables.append(syllable)
        else:
            if syllable in self.selected_last_syllables:
                self.selected_last_syllables.remove(syllable)
                
        self.update_syllable_status()
        
    def select_all_syllables(self):
        """Select all available syllables"""
        self.selected_last_syllables = self.available_last_syllables.copy()
        for var in self.syllable_vars.values():
            var.set(True)
        self.update_syllable_status()
        
    def deselect_all_syllables(self):
        """Deselect all syllables"""
        self.selected_last_syllables = []
        for var in self.syllable_vars.values():
            var.set(False)
        self.update_syllable_status()
        
    def generate_pseudowords(self):
        if not hasattr(self.generator, 'lexicons') or not self.generator.lexicons:
            self.update_status("ERROR: Please load lexicons first.")
            return
            
        # Clear output
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        # Get parameters
        postype = self.postype.get()
        num_syllables = self.num_syllables.get()
        freq_threshold = self.freq_threshold.get()
        sim_threshold = self.sim_threshold.get()
        max_words = self.max_words.get()
        
        # Use selected last syllables if any are selected
        included_last_syllables = self.selected_last_syllables if self.selected_last_syllables else None
        
        self.update_status(f"Starting generation with parameters: POS={postype}, Syllables={num_syllables}, " +
                          f"Freq={freq_threshold}, Sim={sim_threshold}, Max={max_words}")
        
        if included_last_syllables:
            self.update_status(f"Using {len(included_last_syllables)} selected last syllables")
        
        # Create queue for status updates
        status_queue = queue.Queue()
        
        def generate_thread():
            try:
                def status_callback(message):
                    status_queue.put(message)
                
                pseudowords = self.generator.generate_pseudowords(
                    postype=postype,
                    num_syllables=num_syllables,
                    freq_threshold=freq_threshold,
                    sim_threshold=sim_threshold,
                    max_words=max_words,
                    included_last_syllables=included_last_syllables,
                    status_callback=status_callback
                )
                
                # Send results to main thread
                self.root.after(0, lambda: self.display_results(pseudowords))
                
            except Exception as e:
                error_msg = f"Error generating pseudowords: {str(e)}"
                status_queue.put(f"ERROR: {error_msg}")
        
        # Start status update checker
        def check_status():
            try:
                while not status_queue.empty():
                    message = status_queue.get_nowait()
                    self.update_status(message)
                    
                self.root.after(100, check_status)
            except queue.Empty:
                self.root.after(100, check_status)
                
        # Start threads
        threading.Thread(target=generate_thread, daemon=True).start()
        self.root.after(100, check_status)
        
    def display_results(self, pseudowords):
        self.output_text.config(state=tk.NORMAL)
        
        if not pseudowords:
            self.output_text.insert(tk.END, "No pseudowords were generated. Try adjusting parameters.")
        else:
            for i, word in enumerate(pseudowords):
                self.output_text.insert(tk.END, f"{i+1}. {word}\n")
                
        self.output_text.config(state=tk.DISABLED)
        
        # Store current words for other operations
        self.current_words = pseudowords
        
        # Enable import and Greek rules buttons for stress assignment
        self.import_words_btn.config(state="normal")
        self.apply_greek_rules_btn.config(state="normal")
        
    def apply_greek_stress_rules(self):
        """Apply Greek stress rules automatically based on part of speech"""
        if not hasattr(self, 'current_words') or not self.current_words:
            self.update_status("No generated words to apply stress to. Please generate pseudowords first.")
            messagebox.showinfo("Apply Greek Stress Rules", "No generated words available. Please generate pseudowords first.")
            return
        
        # Get the current part of speech selection
        part_of_speech = self.postype.get()
        
        self.update_status(f"Applying Greek stress rules for part of speech: {part_of_speech}")
        
        # Apply stress to each word
        stressed_words = []
        for word in self.current_words:
            try:
                stressed_word = add_random_stress(word, part_of_speech)
                stressed_words.append(stressed_word)
            except Exception as e:
                # If stress application fails, add the word without stress
                stressed_words.append(word)
                self.update_status(f"Warning: Could not apply stress to '{word}': {str(e)}")
        
        # Update the stress input area with the original words
        self.stress_input.delete(1.0, tk.END)
        self.stress_input.insert(1.0, '\n'.join(self.current_words))
        
        # Update the stress output area with the stressed words
        self.stress_output.config(state=tk.NORMAL)
        self.stress_output.delete(1.0, tk.END)
        self.stress_output.insert(1.0, '\n'.join(stressed_words))
        self.stress_output.config(state=tk.DISABLED)
        
        # Enable export buttons
        self.copy_stressed_btn.config(state="normal")
        self.save_stressed_btn.config(state="normal")
        
        self.update_status(f"Applied Greek stress rules to {len(stressed_words)} words using part of speech: {part_of_speech}")
        
    def count_syllables(self, word):
        """Count syllables in a Greek word"""
        # Greek vowels (including diphthongs)
        vowels = "αεηιοωυάέήίόώύΐΰ"
        diphthongs = ["αι", "ει", "οι", "αυ", "ευ", "ηυ", "ου", "υι"]
        
        # Count vowel groups, treating diphthongs as single syllables
        syllable_count = 0
        processed_word = word.lower()
        
        # First, mark diphthongs
        diphthong_positions = []
        for diphthong in diphthongs:
            start = 0
            while True:
                pos = processed_word.find(diphthong, start)
                if pos == -1:
                    break
                for i in range(pos, pos + len(diphthong)):
                    diphthong_positions.append(i)
                start = pos + 1
        
        # Count vowels that aren't part of diphthongs
        for i, char in enumerate(processed_word):
            if char in vowels and i not in diphthong_positions:
                syllable_count += 1
                
        # Add diphthongs as single syllables
        for diphthong in diphthongs:
            syllable_count += processed_word.count(diphthong)
            
        return max(1, syllable_count)  # Ensure at least 1 syllable
    
    def find_vowel_positions(self, word):
        """Find positions of vowels/syllable centers in a Greek word"""
        vowels = "αεηιοωυάέήίόώύΐΰ"
        diphthongs = ["αι", "ει", "οι", "αυ", "ευ", "ηυ", "ου", "υι"]
        
        positions = []
        processed_word = word.lower()
        
        # Find diphthongs first
        diphthong_ranges = []
        for diphthong in diphthongs:
            start = 0
            while True:
                pos = processed_word.find(diphthong, start)
                if pos == -1:
                    break
                diphthong_ranges.append((pos, pos + len(diphthong) - 1))
                positions.append(pos)  # Position of the diphthong (first character)
                start = pos + 1
        
        # Find individual vowels that aren't part of diphthongs
        for i, char in enumerate(processed_word):
            if char in vowels:
                is_in_diphthong = any(start <= i <= end for start, end in diphthong_ranges)
                if not is_in_diphthong:
                    positions.append(i)
        
        return sorted(positions)
    
    def add_stress_to_word(self, word, position):
        """Add stress mark to a Greek word at specified position"""
        # Remove any existing stress marks first
        stress_map_remove = {
            'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ώ': 'ω', 'ύ': 'υ',
            'ΐ': 'ι', 'ΰ': 'υ'
        }
        
        clean_word = word
        for stressed, unstressed in stress_map_remove.items():
            clean_word = clean_word.replace(stressed, unstressed)
        
        vowel_positions = self.find_vowel_positions(clean_word)
        syllable_count = len(vowel_positions)
        
        if syllable_count == 0:
            return word
        
        # Determine which syllable to stress based on position
        if position == 'ultima':
            target_syllable = syllable_count - 1
        elif position == 'penult':
            target_syllable = max(0, syllable_count - 2)
        elif position == 'antepenult':
            target_syllable = max(0, syllable_count - 3)
        else:
            return word
        
        # For words with fewer syllables than required, default to first syllable
        if target_syllable >= syllable_count:
            target_syllable = 0
        
        vowel_index = vowel_positions[target_syllable]
        
        # Apply stress at the vowel position
        return self.apply_stress_at_position(clean_word, vowel_index)
    
    def apply_stress_at_position(self, word, vowel_index):
        """Apply stress mark at a specific character position"""
        diphthongs = {
            'αι': 'αί', 'ει': 'εί', 'οι': 'οί', 
            'αυ': 'αύ', 'ευ': 'εύ', 'ηυ': 'ηύ', 
            'ου': 'ού', 'υι': 'υί'
        }
        
        result = list(word)
        lower_word = word.lower()
        
        # Check if this vowel is the start of a diphthong
        for diphthong, stressed_diphthong in diphthongs.items():
            if (vowel_index < len(lower_word) - 1 and 
                lower_word[vowel_index:vowel_index + 2] == diphthong):
                # Replace the diphthong with its stressed version
                result[vowel_index] = stressed_diphthong[0]
                result[vowel_index + 1] = stressed_diphthong[1]
                return ''.join(result)
        
        # Check if this vowel is the second part of a diphthong
        if vowel_index > 0:
            for diphthong, stressed_diphthong in diphthongs.items():
                if lower_word[vowel_index - 1:vowel_index + 1] == diphthong:
                    # Replace the diphthong with its stressed version
                    result[vowel_index - 1] = stressed_diphthong[0]
                    result[vowel_index] = stressed_diphthong[1]
                    return ''.join(result)
        
        # If not part of a diphthong, apply single vowel stress
        vowel_char = lower_word[vowel_index]
        stress_map = {
            'α': 'ά', 'ε': 'έ', 'η': 'ή', 'ι': 'ί', 'ο': 'ό', 'ω': 'ώ', 'υ': 'ύ'
        }
        
        if vowel_char in stress_map:
            result[vowel_index] = stress_map[vowel_char]
        
        return ''.join(result)
    
    def check_stress_button_state(self, event=None):
        """Enable/disable apply stress button based on input and selections"""
        has_words = bool(self.stress_input.get(1.0, tk.END).strip())
        has_selection = (self.stress_antepenult.get() or 
                        self.stress_penult.get() or 
                        self.stress_ultima.get())
        
        self.apply_stress_btn.config(state="normal" if has_words and has_selection else "disabled")
    
    def import_generated_words(self):
        """Import words from the generation tab"""
        if not hasattr(self, 'current_words') or not self.current_words:
            self.update_status("No generated words to import. Please generate pseudowords first.")
            messagebox.showinfo("Import Words", "No generated words available. Please generate pseudowords first.")
            return
        
        # Clear current stress input and insert generated words
        self.stress_input.delete(1.0, tk.END)
        words_text = '\n'.join(self.current_words)
        self.stress_input.insert(1.0, words_text)
        
        self.update_status(f"Imported {len(self.current_words)} words for stress assignment")
        self.check_stress_button_state()
    
    def apply_stress(self):
        """Apply stress marks to the input words (manual method)"""
        input_text = self.stress_input.get(1.0, tk.END).strip()
        if not input_text:
            messagebox.showwarning("Apply Stress", "No words to stress")
            return
        
        # Get selected stress positions
        selected_positions = []
        if self.stress_antepenult.get():
            selected_positions.append('antepenult')
        if self.stress_penult.get():
            selected_positions.append('penult')
        if self.stress_ultima.get():
            selected_positions.append('ultima')
        
        if not selected_positions:
            messagebox.showwarning("Apply Stress", "Please select at least one stress position")
            return
        
        words = [word.strip() for word in input_text.split('\n') if word.strip()]
        stressed_words = []
        
        for index, word in enumerate(words):
            syllable_count = self.count_syllables(word)
            
            # Determine stress position
            if len(selected_positions) == 1:
                stress_position = selected_positions[0]
            else:
                # Multiple positions selected - distribute evenly
                if syllable_count == 2:
                    # For 2-syllable words, use 50-50 distribution between ultima and penult
                    valid_positions = [pos for pos in selected_positions 
                                     if pos in ['ultima', 'penult']]
                    if valid_positions:
                        stress_position = valid_positions[index % len(valid_positions)]
                    else:
                        stress_position = selected_positions[index % len(selected_positions)]
                else:
                    # For 3+ syllable words, distribute evenly among all selected positions
                    stress_position = selected_positions[index % len(selected_positions)]
            
            stressed_word = self.add_stress_to_word(word, stress_position)
            stressed_words.append(stressed_word)
        
        # Display results
        self.stress_output.config(state=tk.NORMAL)
        self.stress_output.delete(1.0, tk.END)
        self.stress_output.insert(1.0, '\n'.join(stressed_words))
        self.stress_output.config(state=tk.DISABLED)
        
        # Enable export buttons
        self.copy_stressed_btn.config(state="normal")
        self.save_stressed_btn.config(state="normal")
        
        self.update_status(f"Applied manual stress to {len(stressed_words)} words using {', '.join(selected_positions)} distribution")
    
    def clear_stress(self):
        """Clear stress assignment input and output"""
        self.stress_input.delete(1.0, tk.END)
        self.stress_output.config(state=tk.NORMAL)
        self.stress_output.delete(1.0, tk.END)
        self.stress_output.config(state=tk.DISABLED)
        
        # Disable export buttons
        self.copy_stressed_btn.config(state="disabled")
        self.save_stressed_btn.config(state="disabled")
        
        self.check_stress_button_state()
        self.update_status("Stress assignment area cleared")
    
    def copy_stressed_words(self):
        """Copy stressed words to clipboard"""
        stressed_text = self.stress_output.get(1.0, tk.END).strip()
        if not stressed_text:
            messagebox.showinfo("Copy", "No stressed words to copy")
            return
        
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(stressed_text)
            self.update_status("Copied stressed words to clipboard")
            messagebox.showinfo("Copy", "Stressed words copied to clipboard")
        except Exception as e:
            self.update_status(f"Error copying to clipboard: {str(e)}")
            messagebox.showerror("Copy Error", f"Failed to copy to clipboard: {str(e)}")
    
    def save_stressed_words(self):
        """Save stressed words to file"""
        stressed_text = self.stress_output.get(1.0, tk.END).strip()
        if not stressed_text:
            messagebox.showinfo("Save", "No stressed words to save")
            return
        
        # Ask for file path
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"), 
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # Determine file format
            is_csv = file_path.lower().endswith('.csv')
            
            with open(file_path, 'w', encoding='utf-8') as file:
                if is_csv:
                    # Write CSV format with BOM for Excel compatibility
                    file.write('\ufeff')  # BOM
                    file.write('Stressed_Pseudoword\n')
                    
                    words = [word.strip() for word in stressed_text.split('\n') if word.strip()]
                    for word in words:
                        file.write(f'"{word}"\n')
                else:
                    # Write plain text format
                    file.write(stressed_text)
            
            self.update_status(f"Saved stressed words to {file_path}")
            messagebox.showinfo("Save", f"Stressed words saved to {file_path}")
            
        except Exception as e:
            self.update_status(f"Error saving file: {str(e)}")
            messagebox.showerror("Save Error", f"Failed to save file: {str(e)}")
        
    def sort_alphabetically(self):
        """Sort current words alphabetically"""
        if not hasattr(self, 'current_words') or not self.current_words:
            self.update_status("No words to sort.")
            return
            
        sorted_words = sorted(self.current_words)
        self.current_words = sorted_words
        
        # Update display
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        for i, word in enumerate(sorted_words):
            self.output_text.insert(tk.END, f"{i+1}. {word}\n")
        self.output_text.config(state=tk.DISABLED)
        
        self.update_status("Words sorted alphabetically.")
        
    def randomize_order(self):
        """Randomize the order of current words"""
        if not hasattr(self, 'current_words') or not self.current_words:
            self.update_status("No words to randomize.")
            return
            
        randomized_words = self.current_words.copy()
        random.shuffle(randomized_words)
        self.current_words = randomized_words
        
        # Update display
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        for i, word in enumerate(randomized_words):
            self.output_text.insert(tk.END, f"{i+1}. {word}\n")
        self.output_text.config(state=tk.DISABLED)
        
        self.update_status("Words randomized.")
        
    def save_to_file(self):
        # Get content from output text
        self.output_text.config(state=tk.NORMAL)
        content = self.output_text.get(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        if not content.strip():
            messagebox.showinfo("Save to File", "No pseudowords to save.")
            return
            
        # Ask for file path
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"), 
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
            
        try:
            # Determine file format
            is_csv = file_path.lower().endswith('.csv')
            
            with open(file_path, 'w', encoding='utf-8') as file:
                if is_csv:
                    # Write CSV format with BOM for Excel compatibility
                    file.write('\ufeff')  # BOM
                    file.write('Pseudoword\n')
                    
                    # Extract just the words without numbers
                    for line in content.strip().split('\n'):
                        if line.strip():
                            parts = line.split('.', 1)
                            if len(parts) > 1:
                                word = parts[1].strip()
                                file.write(f'"{word}"\n')
                else:
                    # Write plain text format
                    words_only = []
                    for line in content.strip().split('\n'):
                        if line.strip():
                            parts = line.split('.', 1)
                            if len(parts) > 1:
                                words_only.append(parts[1].strip())
                    
                    # Write one word per line
                    file.write('\n'.join(words_only))
                
            self.update_status(f"Saved pseudowords to {file_path}")
            
        except Exception as e:
            self.update_status(f"Error saving file: {str(e)}")


# Create and run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = PseudowordGeneratorApp(root)
    root.mainloop()import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import pandas as pd
import numpy as np
import itertools
import os
import threading
import queue
import time
import random
import json

# You'll need to install these packages:
# pip install pandas numpy jellyfish greek-accentuation tkinter

try:
    import jellyfish
except ImportError:
    messagebox.showerror("Missing Package", "Please install jellyfish: pip install jellyfish")

try:
    from greek_accentuation.syllabify import syllabify
    from greek_accentuation.characters import remove_diacritic, add_diacritic
except ImportError:
    messagebox.showerror("Missing Package", "Please install greek-accentuation: pip install greek-accentuation")

def add_random_stress(word, part_of_speech="All"):
    """
    Adds an acute accent (oxia) to the last vowel of a randomly chosen eligible syllable
    (ultima, penult, or antepenult) of a Greek word following Greek stress rules.
    
    Stress Rules:
    - For verbs ending in -αι: stress is NEVER on the ultima (final syllable)
    - For all other verb forms: stress is NEVER on the antepenult (APU)
    - For non-verbs: standard Greek stress rules apply (ultima, penult, or antepenult)
    
    Returns the stressed word.
    """
    vowels = 'αεηιουω'
    sylls = syllabify(word)
    n = len(sylls)
    
    # Initialize eligible positions (using negative indexing: -1=ultima, -2=penult, -3=antepenult)
    eligible = []
    
    if part_of_speech == "verb":
        # Check if verb ends in -αι
        if word.endswith("αι"):
            # Rule: stress is NEVER on the ultima for verbs ending in -αι
            # So eligible positions are penult and antepenult only
            if n >= 2:
                eligible.append(-2)  # penult
            if n >= 3:
                eligible.append(-3)  # antepenult
        else:
            # Rule: for all other verb forms, stress is NEVER on the antepenult
            # So eligible positions are ultima and penult only
            eligible.append(-1)  # ultima
            if n >= 2:
                eligible.append(-2)  # penult
    else:
        # For non-verbs: standard Greek stress rules (can be on any of the last 3 syllables)
        eligible.append(-1)  # ultima
        if n >= 2:
            eligible.append(-2)  # penult
        if n >= 3:
            eligible.append(-3)  # antepenult
    
    # If no eligible positions (shouldn't happen with valid Greek words), default to ultima
    if not eligible:
        eligible = [-1]
    
    # Randomly choose from eligible positions
    target = np.random.choice(eligible)
    syll = sylls[target]
    
    # Find the last vowel in the target syllable
    last_vowel_idx = None
    for i, char in enumerate(syll):
        if char in vowels:
            last_vowel_idx = i
    
    if last_vowel_idx is not None:
        stressed_vowel = add_diacritic(syll[last_vowel_idx], '\u0301')  # oxia
        sylls[target] = syll[:last_vowel_idx] + stressed_vowel + syll[last_vowel_idx+1:]
    
    return ''.join(sylls)

class GreekPseudowordGenerator:
    def __init__(self):
        self.lexicons = {}
        self.combined_lex = set()
        # Define function to remove oxia
        try:
            self.remove_oxia = remove_diacritic("\u0301")
        except NameError:
            # Fallback if greek_accentuation isn't available
            self.remove_oxia = lambda s: s
        
    def load_lexicons(self, greeklex_path, all_num_clean_path=None):
        """Load lexicons from files"""
        # Load first lexicon
        try:
            print(f"Loading primary lexicon from {greeklex_path}...")
            self.lexicons["greeklex"] = pd.read_excel(greeklex_path)
            # Convert Word column to string to avoid type issues
            self.lexicons["greeklex"]["Word"] = self.lexicons["greeklex"]["Word"].astype(str)
            self.lexicons["greeklex"]["Word"] = self.lexicons["greeklex"]["Word"].apply(self.remove_oxia)
            
            # Initialize combined lexicon with first lexicon
            self.combined_lex = set(self.lexicons["greeklex"]["Word"].values)
            
            # Load second lexicon if provided
            if all_num_clean_path:
                print(f"Loading secondary lexicon from {all_num_clean_path}...")
                try:
                    excel_file = pd.ExcelFile(all_num_clean_path)
                    dfs = []
                    for sheet_name in excel_file.sheet_names:
                        dftemp = excel_file.parse(sheet_name)
                        dfs.append(dftemp)
                    self.lexicons["all_num_clean"] = pd.concat(dfs, ignore_index=True)
                    
                    # Check if 'spel' column exists in second lexicon
                    if 'spel' in self.lexicons["all_num_clean"].columns:
                        # Ensure values are strings
                        self.lexicons["all_num_clean"]["spel"] = self.lexicons["all_num_clean"]["spel"].astype(str)
                        # Add to combined lexicon
                        self.combined_lex.update(set(self.lexicons["all_num_clean"]["spel"].values))
                    else:
                        print("Warning: 'spel' column not found in second lexicon.")
                        # List columns found in the second lexicon
                        print(f"Columns found: {list(self.lexicons['all_num_clean'].columns)}")
                except Exception as e:
                    print(f"Warning: Could not fully process second lexicon: {e}")
            
            return self.get_available_pos()
        except Exception as e:
            print(f"Error loading lexicons: {e}")
            raise
        
    def get_available_pos(self):
        """Return available parts of speech in the lexicon"""
        return np.unique(self.lexicons["greeklex"].Pos.values).tolist()
    
    def phonetic_string(self, input_string):
        """Convert string to phonetic representation"""
        if not isinstance(input_string, str):
            input_string = str(input_string)
            
        substitutions = {
            "αι": "ε",
            "ει": "ι",
            "οι": "ι",
            "υι": "ι",
            "ω": "ο",
            "η": "ι",
            "υ": "ι"
        }
        output_string = input_string
        for pattern, replacement in substitutions.items():
            output_string = output_string.replace(pattern, replacement)
        return output_string
    
    def max_consecutively_repeated_letters(self, string):
        """Count maximum consecutively repeated letters"""
        if not isinstance(string, str):
            string = str(string)
            
        max_count = 0
        current_count = 0
        previous_letter = None

        for letter in string:
            if letter.isalpha():
                letter = letter.lower()
                if letter == previous_letter:
                    current_count += 1
                else:
                    current_count = 1
                    previous_letter = letter

                if current_count > max_count:
                    max_count = current_count
        return max_count
    
    def calculate_similarity(self, string1, string2):
        """Calculate similarity between two strings"""
        # Ensure inputs are strings
        if not isinstance(string1, str):
            string1 = str(string1)
        if not isinstance(string2, str):
            string2 = str(string2)
            
        levenshtein_distance = jellyfish.levenshtein_distance(string1, string2)
        similarity_ratio = 1 - (levenshtein_distance / max(len(string1), len(string2)))
        return similarity_ratio
    
    def generate_ngrams(self, text):
        """Generate n-grams from text"""
        if not isinstance(text, str):
            text = str(text)
            
        ngrams_2 = [text[i:i+2] for i in range(len(text)-1)]
        ngrams_3 = [text[i:i+3] for i in range(len(text)-2)]
        return ngrams_2, ngrams_3
    
    def search_ngrams_in_lexicon(self, ngrams_2, ngrams_3):
        """Search n-grams in lexicon"""
        for ngram in ngrams_2 + ngrams_3:
            found = False
            for word in self.combined_lex:
                if ngram in word:
                    found = True
                    break
            if not found:
                return False
        return True
    
    def accept_reject_tests(self, string1, simthreshold=0.5):
        """Apply tests to accept or reject pseudowords"""
        # Ensure input is a string
        if not isinstance(string1, str):
            string1 = str(string1)
            
        # Test 1: Reject if the word exists in the lexicon
        if string1 in self.combined_lex:
            return False
        
        # Test 2: Reject if there are consecutively repeated letters
        if self.max_consecutively_repeated_letters(string1) > 1:
            return False
        
        # Test 3: Check similarity and phonetic_similarity
        # For performance, sample a subset of the lexicon
        lexicon_sample = random.sample(list(self.combined_lex), min(1000, len(self.combined_lex)))
        for string2 in lexicon_sample:
            similarity_ratio = self.calculate_similarity(string1, string2)
            phonetic_similarity_ratio = self.calculate_similarity(
                self.phonetic_string(string1), self.phonetic_string(string2))
            check_ratio = max(similarity_ratio, phonetic_similarity_ratio)
            if check_ratio > simthreshold:
                return False
                
        # Test 4: Check if all n-grams exist in the lexicon
        ngrams_2, ngrams_3 = self.generate_ngrams(string1)
        test = self.search_ngrams_in_lexicon(ngrams_2, ngrams_3)
        if not test:
            return False

        return True

    def get_balanced_syllable_samples(self, syldict, num_samples=100):
        """
        Create a balanced sample of syllable combinations to ensure variety in first syllables
        """
        balanced_samples = []
        
        # Get unique first syllables
        first_syllables = list(syldict[1])
        
        # If there are too few first syllables, just return regular combinations
        if len(first_syllables) <= 1:
            return None
            
        # Calculate how many samples to take for each first syllable
        samples_per_first_syllable = max(1, num_samples // len(first_syllables))
        
        # For each first syllable, create some combinations
        for first_syl in first_syllables:
            # Create list of syllables with this specific first syllable
            syllable_list = [[first_syl]]
            
            # Add other syllable positions
            for pos in range(2, len(syldict) + 1):
                syllable_list.append(list(syldict[pos]))
                
            # Generate some combinations with this first syllable
            for _ in range(samples_per_first_syllable):
                combination = [first_syl]
                for pos in range(1, len(syldict)):
                    combination.append(random.choice(syllable_list[pos]))
                balanced_samples.append(combination)
                
        # Shuffle the samples
        random.shuffle(balanced_samples)
        return balanced_samples
    
    def get_syllable_dict(self, postype="noun", num_syllables=3, freq_threshold=5, status_callback=None):
        """Generate syllable dictionary without generating words"""
        # Send status update
        if status_callback:
            status_callback(f"Analyzing {num_syllables}-syllable words for part of speech: {postype}...")
        
        # Filter words by part of speech and frequency
        filtered_df = self.lexicons["greeklex"][
            (self.lexicons["greeklex"].Pos == postype) & 
            (self.lexicons["greeklex"].zipfFreq > freq_threshold)
        ]
        
        # Extract Word column as a Series
        df = filtered_df["Word"]
        
        # Create syllable dictionary
        syldict = dict()
        for n in range(num_syllables):
            syldict[n+1] = list()

        # Collect syllables from filtered words
        for wrd in df.values:
            if isinstance(wrd, str):
                q = self.remove_oxia(wrd)
                try:
                    sl = syllabify(q)
                    if len(sl) == num_syllables:
                        for n in range(num_syllables):
                            syldict[n+1].append(sl[n])
                except Exception as e:
                    continue

        # Get unique syllables
        for k, v in syldict.items():
            syldict[k] = np.unique(v)
            
        # Check if we have enough syllables to generate words
        empty_positions = [k for k, v in syldict.items() if len(v) == 0]
        if empty_positions:
            error_msg = f"Not enough syllables for position(s): {empty_positions}"
            if status_callback:
                status_callback(f"ERROR: {error_msg}")
            return None
            
        # Send status update about syllable counts
        if status_callback:
            syllable_info = ", ".join([f"Position {k}: {len(v)} syllables" for k, v in syldict.items()])
            status_callback(f"Found syllables: {syllable_info}")
            
        return syldict
    
    def generate_pseudowords_with_syllables(self, syldict, included_last_syllables=None, 
                                           sim_threshold=0.8, max_words=100, status_callback=None):
        """Generate pseudowords with specific syllable constraints"""
        # Track the number of words generated
        count = 0
        attempts = 0
        max_attempts = max_words * 100  # Limit attempts to avoid infinite loops
        accepted_words = []
        
        # Filter last syllables if specified
        if included_last_syllables and len(syldict) >= 3:
            # Create a copy to avoid modifying the original
            filtered_syldict = dict(syldict)
            # Filter last syllables (position = len(syldict))
            filtered_syldict[len(syldict)] = np.array([s for s in syldict[len(syldict)] 
                                                    if s in included_last_syllables])
            # Check if we have any syllables left
            if len(filtered_syldict[len(syldict)]) == 0:
                if status_callback:
                    status_callback("ERROR: No last syllables remaining after filtering")
                return []
            syldict = filtered_syldict
            
            if status_callback:
                status_callback(f"Using {len(syldict[len(syldict)])} selected last syllables")
        
        # Try to get balanced samples to ensure variety in first syllables
        balanced_samples = self.get_balanced_syllable_samples(syldict, max_words * 5)
        
        if balanced_samples:
            # Use balanced samples for better variety
            if status_callback:
                status_callback("Using balanced sampling to ensure variety in first syllables...")
            
            # Test the balanced samples
            for combination in balanced_samples:
                attempts += 1
                if count >= max_words or attempts >= max_attempts:
                    break
                    
                joined_string = ''.join(combination)
                
                if self.accept_reject_tests(joined_string, sim_threshold):
                    accepted_words.append(joined_string)
                    count += 1
                    
                    if status_callback and count % 5 == 0:
                        status_callback(f"Generated {count} pseudowords...")
        else:
            # Fallback to traditional method
            if status_callback:
                status_callback("Using standard sampling method...")
                
            # Standard method using itertools
            import itertools
            iterlist = [list(v) for v in syldict.values()]
            for entry in itertools.product(*iterlist):
                attempts += 1
                if count >= max_words or attempts >= max_attempts:
                    break
                    
                joined_string = ''.join(entry)
                
                if self.accept_reject_tests(joined_string, sim_threshold):
                    accepted_words.append(joined_string)
                    count += 1
                    
                    if status_callback and count % 5 == 0:
                        status_callback(f"Generated {count} pseudowords...")
                    
        if status_callback:
            status_callback(f"COMPLETE: Generated {len(accepted_words)} pseudowords.")
            
        return accepted_words
    
    def generate_pseudowords(self, postype="noun", num_syllables=3, freq_threshold=5, sim_threshold=0.8, 
                            max_words=100, included_last_syllables=None, status_callback=None):
        """Generate pseudowords"""
        # Send status update
        if status_callback:
            status_callback(f"Generating {num_syllables}-syllable pseudowords for part of speech: {postype}...")
            
        # Handle "all" option - process all five POS types
        if postype == "all":
            postypes = ["noun", "verb", "adj", "adv", "prep"]
            words_per_type = max(1, max_words // len(postypes))  # Distribute words evenly
            if status_callback:
                status_callback(f"Processing all parts of speech: {', '.join(postypes)}")
            
            generated_words = []
            for pos in postypes:
                if status_callback:
                    status_callback(f"Generating {words_per_type} {pos} pseudowords...")
                
                # Get syllable dictionary for this POS
                syldict = self.get_syllable_dict(pos, num_syllables, freq_threshold, status_callback)
                
                if not syldict:
                    if status_callback:
                        status_callback(f"Skipping {pos} due to insufficient syllables")
                    continue
                    
                # Generate pseudowords with the syllable dictionary
                pos_words = self.generate_pseudowords_with_syllables(
                    syldict,
                    included_last_syllables=included_last_syllables,
                    sim_threshold=sim_threshold,
                    max_words=words_per_type,
                    status_callback=status_callback
                )
                generated_words.extend(pos_words)
                if status_callback:
                    status_callback(f"Generated {len(pos_words)} {pos} pseudowords")
            
            if status_callback:
                status_callback(f"Total pseudowords generated: {len(generated_words)}")
            return generated_words
        else:
            # Original logic for a single POS type
            # Get syllable dictionary
            syldict = self.get_syllable_dict(postype, num_syllables, freq_threshold, status_callback)
            
            if not syldict:
                return []
                
            # Generate pseudowords with the syllable dictionary
            return self.generate_pseudowords_with_syllables(
                syldict,
                included_last_syllables=included_last_syllables,
                sim_threshold=sim_threshold,
                max_words=max_words,
                status_callback=status_callback
            )


class PseudowordGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SyBig-r-Morph - Greek Pseudoword Generator")
        self.root.geometry("900x800")
        self.generator = GreekPseudowordGenerator()
        self.available_pos = []
        self.available_last_syllables = []
        self.selected_last_syllables = []
        self.current_syllable_params = {}
        self.setup_ui()
        
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main generation tab
        main_frame = ttk.Frame(notebook, padding="10")
        notebook.add(main_frame, text="Generation")
        
        # Syllable selection tab
        syllable_frame = ttk.Frame(notebook, padding="10")
        notebook.add(syllable_frame, text="Last Syllable Selection")
        
        # Stress assignment tab
        stress_frame = ttk.Frame(notebook, padding="10")
        notebook.add(stress_frame, text="Stress Assignment")
        
        # Setup main generation tab
        self.setup_main_tab(main_frame)
        
        # Setup syllable selection tab
        self.setup_syllable_tab(syllable_frame)
        
        # Setup stress assignment tab
        self.setup_stress_tab(stress_frame)
        
    def setup_main_tab(self, parent):
        # Lexicon files section
        files_frame = ttk.LabelFrame(parent, text="Lexicon Files", padding="10")
        files_frame.pack(fill=tk.X, pady=10)
        
        # GreekLex2 file
        ttk.Label(files_frame, text="GreekLex2.xlsx:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.greeklex_path = tk.StringVar(value="GreekLex2.xlsx")
        ttk.Entry(files_frame, textvariable=self.greeklex_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.greeklex_path)).grid(row=0, column=2)
        
        # All_num_clean file
        ttk.Label(files_frame, text="all_num_clean_ns.xls:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.all_num_clean_path = tk.StringVar(value="all_num_clean_ns.xls")
        ttk.Entry(files_frame, textvariable=self.all_num_clean_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(files_frame, text="Browse", command=lambda: self.browse_file(self.all_num_clean_path)).grid(row=1, column=2)
        
        # Load lexicons button
        ttk.Button(files_frame, text="Load Lexicons", command=self.load_lexicons).grid(row=2, column=0, columnspan=3, pady=10)
        
        # Parameters section
        params_frame = ttk.LabelFrame(parent, text="Generation Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=10)
        
        # Part of speech
        ttk.Label(params_frame, text="Part of Speech:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.postype = ttk.Combobox(params_frame, state="disabled")
        self.postype.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.postype.bind('<<ComboboxSelected>>', self.on_param_change)
        
        # Number of syllables
        ttk.Label(params_frame, text="Number of Syllables:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.num_syllables = tk.IntVar(value=3)
        syllable_spinbox = ttk.Spinbox(params_frame, from_=1, to=5, textvariable=self.num_syllables, width=5)
        syllable_spinbox.grid(row=1, column=1, sticky=tk.W, padx=5)
        syllable_spinbox.bind('<KeyRelease>', self.on_param_change)
        syllable_spinbox.bind('<<Increment>>', self.on_param_change)
        syllable_spinbox.bind('<<Decrement>>', self.on_param_change)
        
        # Frequency threshold
        ttk.Label(params_frame, text="Frequency Threshold:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.freq_threshold = tk.DoubleVar(value=5.0)
        freq_spinbox = ttk.Spinbox(params_frame, from_=0, to=10, increment=0.1, textvariable=self.freq_threshold, width=5)
        freq_spinbox.grid(row=2, column=1, sticky=tk.W, padx=5)
        freq_spinbox.bind('<KeyRelease>', self.on_param_change)
        freq_spinbox.bind('<<Increment>>', self.on_param_change)
        freq_spinbox.bind('<<Decrement>>', self.on_param_change)
        
        # Similarity threshold
        ttk.Label(params_frame, text="Similarity Threshold:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.sim_threshold = tk.DoubleVar(value=0.8)
        ttk.Spinbox(params_frame, from_=0.1, to=1.0, increment=0.1, textvariable=self.sim_threshold, width=5).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # Max words
        ttk.Label(params_frame, text="Maximum Words:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.max_words = tk.IntVar(value=100)
        ttk.Spinbox(params_frame, from_=1, to=1000, textvariable=self.max_words, width=5).grid(row=4, column=1, sticky=tk.W, padx=5)
        
        # Last syllable selection status
        ttk.Label(params_frame, text="Last Syllables:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.syllable_status_label = ttk.Label(params_frame, text="No syllables selected")
        self.syllable_status_label.grid(row=5, column=1, sticky=tk.W, padx=5)
        
        # Generate button
        self.generate_button = ttk.Button(params_frame, text="Generate Pseudowords", command=self.generate_pseudowords, state="disabled")
        self.generate_button.grid(row=6, column=0, columnspan=2, pady=10)
        
        # Status and output section
        output_frame = ttk.LabelFrame(parent, text="Status and Results", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Status box
        ttk.Label(output_frame, text="Status:").pack(anchor=tk.W)
        self.status_text = scrolledtext.ScrolledText(output_frame, height=5, wrap=tk.WORD)
        self.status_text.pack(fill=tk.X, pady=5)
        self.status_text.config(state=tk.DISABLED)
        
        # Output box
        ttk.Label(output_frame, text="Generated Pseudowords:").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.output_text.config(state=tk.DISABLED)
        
        # Buttons frame
        buttons_frame = ttk.Frame(output_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        
        # Save button
        ttk.Button(buttons_frame, text="Save to File", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        
        # Sort buttons
        ttk.Button(buttons_frame, text="Sort A-Z", command=self.sort_alphabetically).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Randomize", command=self.randomize_order).pack(side=tk.LEFT, padx=5)
        
    def setup_syllable_tab(self, parent):
        # Instructions
        instructions = ttk.Label(parent, text="Select specific last syllables to use in generation (optional):", 
                                font=('TkDefaultFont', 10, 'bold'))
        instructions.pack(anchor=tk.W, pady=(0, 10))
        
        # Control buttons frame
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="Load Available Syllables", 
                  command=self.load_syllables).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Select All", 
                  command=self.select_all_syllables).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Deselect All", 
                  command=self.deselect_all_syllables).pack(side=tk.LEFT, padx=5)
        
        # Search frame
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=5)
        self.search_var.trace('w', self.filter_syllables)
        
        # Status label for syllables
        self.syllable_count_label = ttk.Label(parent, text="")
        self.syllable_count_label.pack(anchor=tk.W, pady=5)
        
        # Syllable selection area
        syllable_container = ttk.Frame(parent)
        syllable_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create scrollable frame for syllables
        self.syllable_canvas = tk.Canvas(syllable_container)
        scrollbar = ttk.Scrollbar(syllable_