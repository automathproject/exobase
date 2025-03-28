"""
Module for analyzing LaTeX exercise files and generating metadata using Gemini API.
This module provides functionality for extracting metadata and resumés from LaTeX files.
"""

import os
import re
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Dict, List, Optional, Any, Union, Callable

# Import prompts from separate module
from prompts import create_metadata_prompt, create_resume_prompt

# Load environment variables from .env file
load_dotenv()
api_key = os.environ.get("cle_gemini_api")
if not api_key:
    raise ValueError("La clé API n'est pas définie dans le fichier .env. Veuillez configurer la variable 'cle_gemini_api'.")

# Configure Gemini API
genai.configure(api_key=api_key)

def extract_uuid(content: str) -> Optional[str]:
    """Extract UUID from LaTeX content."""
    uuid_match = re.search(r'\\uuid\{([^}]+)\}', content)
    return uuid_match.group(1) if uuid_match else None

def extract_json_from_response(text_response: str, debug: bool = False) -> Dict[str, Any]:
    """
    Extract JSON data from API response with multiple fallback methods.
    Works with both metadata and resume extraction.
    """
    if debug:
        print("\n=== RÉPONSE BRUTE DE L'API ===")
        print(text_response)
        print("==============================\n")
    
    # Method 1: Direct JSON parsing
    try:
        return json.loads(text_response)
    except json.JSONDecodeError:
        pass
    
    # Method 2: Markdown JSON block
    json_match = re.search(r'```json\n([\s\S]*?)\n```', text_response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # Method 3: Generic code block
    json_match = re.search(r'```\n([\s\S]*?)\n```', text_response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # Method 4: Find anything that looks like JSON
    json_match = re.search(r'\{[\s\S]*\}', text_response)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    # Method 5: Direct extraction of resume if exists (for resume extraction)
    resume_match = re.search(r'"resume"\s*:\s*"([\s\S]*?)(?:"(?=\s*})|"(?=\s*,))', text_response)
    if resume_match:
        resume_content = resume_match.group(1)
        return {"resume": resume_content}
    
    # Last resort
    if debug:
        print("ERREUR: Impossible d'extraire un JSON valide de la réponse.")
    
    # Return minimal structure with raw text as a last resort
    return {"extraction_error": "EXTRACTION MANUELLE NÉCESSAIRE: " + text_response[:300] + "..."}

def process_latex_file(
    file_path: str, 
    output_dir: str, 
    process_type: str,
    model_name: str = "gemini-2.0-flash", 
    force_reprocess: bool = False, 
    debug: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Process a single LaTeX file to extract metadata, résumé, or both.
    
    Args:
        file_path: Path to the LaTeX file
        output_dir: Directory to save output
        process_type: Type of processing ('metadata', 'resume', or 'both')
        model_name: Gemini model to use
        force_reprocess: Whether to reprocess existing files
        debug: Whether to print debug information
        
    Returns:
        Dictionary with UUID and extracted data, or None if processing failed
    """
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract UUID
        uuid = extract_uuid(content)
        if not uuid:
            print(f"UUID non trouvé dans le fichier {file_path}")
            return None
        
        # Create output directories (main dir and uuid subdirectory)
        output_uuid_dir = os.path.join(output_dir, 'exercises')
        os.makedirs(output_uuid_dir, exist_ok=True)
        
        # Define output file path
        output_file = os.path.join(output_uuid_dir, f"{uuid}.json")
        
        # Check if file exists and skip processing if it does (unless force_reprocess is True)
        if os.path.exists(output_file) and not force_reprocess:
            print(f"Fichier {uuid} déjà traité, ignoré.")
            return {"uuid": uuid, "status": "skipped"}
            
        # Create or load existing data
        existing_data = {}
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                
        # Create result structure if it doesn't exist
        if uuid not in existing_data:
            existing_data[uuid] = {}
        
        # Process metadata if needed
        if process_type in ['metadata', 'both']:
            print(f"Extraction des métadonnées pour {uuid}...")
            prompt = create_metadata_prompt(content)
            
            if debug:
                print("\n=== PROMPT MÉTADONNÉES ===")
                print(prompt)
                print("=========================\n")
            
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                json_data = extract_json_from_response(response.text, debug)
                
                # Update the existing data with new metadata
                existing_data[uuid].update(json_data)
            except Exception as e:
                print(f"ERREUR lors de l'extraction des métadonnées pour {uuid}: {e}")
                if debug and 'response' in locals():
                    print(f"Réponse brute: {response.text}")
        
        # Process resume if needed
        if process_type in ['resume', 'both']:
            print(f"Extraction du résumé pour {uuid}...")
            prompt = create_resume_prompt(content)
            
            if debug:
                print("\n=== PROMPT RÉSUMÉ ===")
                print(prompt)
                print("====================\n")
            
            try:
                # Add a small delay if we just did a metadata extraction
                if process_type == 'both':
                    time.sleep(1.0)
                    
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                json_data = extract_json_from_response(response.text, debug)
                
                # Add resume to existing data
                if "resume" in json_data:
                    existing_data[uuid]["resume"] = json_data["resume"]
            except Exception as e:
                print(f"ERREUR lors de l'extraction du résumé pour {uuid}: {e}")
                if debug and 'response' in locals():
                    print(f"Réponse brute: {response.text}")
        
        # Write updated data to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        return existing_data
        
    except Exception as e:
        print(f"Erreur lors de l'analyse du fichier {file_path}: {e}")
        return None

def process_latex_files(
    source_dir: str, 
    output_dir: str, 
    process_type: str = 'both',
    model_name: str = "gemini-2.0-flash", 
    max_files: Optional[int] = None, 
    api_delay: float = 1.0, 
    force_reprocess: bool = False, 
    debug: bool = False,
    analysis_only: bool = False
) -> Dict[str, Any]:
    """
    Process multiple LaTeX files in a directory.
    
    Args:
        source_dir: Directory containing LaTeX files
        output_dir: Directory to save output
        process_type: Type of processing ('metadata', 'resume', or 'both')
        model_name: Gemini model to use
        max_files: Maximum number of files to process (None for all)
        api_delay: Delay between API calls in seconds
        force_reprocess: Whether to reprocess existing files
        debug: Whether to print debug information
        analysis_only: If True, skips API calls and just analyzes what would be done
        
    Returns:
        Dictionary with combined results
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create exercises directory
    exercises_dir = os.path.join(output_dir, 'exercises')
    os.makedirs(exercises_dir, exist_ok=True)
    
    # Get all .tex files in source directory
    files = [str(f) for f in Path(source_dir).glob('**/*.tex')]
    
    # Limit number of files if requested
    if max_files:
        files = files[:max_files]
        print(f"Mode test: limité à {max_files} fichiers")
    
    print(f"Traitement de {len(files)} fichiers LaTeX...")
    
    # Process each file
    combined_results = {}
    success_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, file in enumerate(files):
        print(f"\n[{i+1}/{len(files)}] Analyse de {os.path.basename(file)}...")
        
        # Analysis only mode
        if analysis_only:
            # Extract UUID from file to check if it would be processed
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            uuid = extract_uuid(content)
            if not uuid:
                print(f"UUID non trouvé dans le fichier {file}")
                failed_count += 1
                continue
                
            output_file = os.path.join(exercises_dir, f"{uuid}.json")
            if os.path.exists(output_file) and not force_reprocess:
                print(f"Fichier {uuid} déjà traité, serait ignoré.")
                skipped_count += 1
            else:
                print(f"Fichier {uuid} serait traité.")
                success_count += 1
            continue
        
        # Actual processing
        result = process_latex_file(
            file_path=file, 
            output_dir=output_dir, 
            process_type=process_type,
            model_name=model_name, 
            force_reprocess=force_reprocess, 
            debug=debug
        )
        
        if result is None:
            failed_count += 1
        elif "status" in result and result["status"] == "skipped":
            skipped_count += 1
        else:
            combined_results.update(result)
            success_count += 1
        
        # Pause before next file (if not last file)
        if i < len(files) - 1 and result is not None and "status" not in result:
            print(f"Pause de {api_delay} secondes...")
            time.sleep(api_delay)
    
    # Write all results to a single file (if not in analysis only mode)
    if not analysis_only and combined_results:
        with open(os.path.join(output_dir, 'all_results.json'), 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, ensure_ascii=False, indent=2)
    
    if analysis_only:
        print(f"Analyse terminée. {success_count} fichiers seraient traités, {skipped_count} seraient ignorés, {failed_count} échoueraient.")
    else:
        print(f"Traitement terminé. {success_count} fichiers analysés avec succès, {skipped_count} ignorés, {failed_count} échoués.")
    
    return combined_results

# Convenience functions
def extract_metadata(
    source_dir: str, 
    output_dir: str, 
    model_name: str = "gemini-2.0-flash", 
    max_files: Optional[int] = None, 
    api_delay: float = 1.0, 
    force_reprocess: bool = False, 
    debug: bool = False,
    analysis_only: bool = False
) -> Dict[str, Any]:
    """Extract metadata from LaTeX files."""
    return process_latex_files(
        source_dir=source_dir,
        output_dir=output_dir,
        process_type='metadata',
        model_name=model_name,
        max_files=max_files,
        api_delay=api_delay,
        force_reprocess=force_reprocess,
        debug=debug,
        analysis_only=analysis_only
    )

def extract_resume(
    source_dir: str, 
    output_dir: str, 
    model_name: str = "gemini-2.0-flash", 
    max_files: Optional[int] = None, 
    api_delay: float = 1.0, 
    force_reprocess: bool = False, 
    debug: bool = False,
    analysis_only: bool = False
) -> Dict[str, Any]:
    """Extract resumés from LaTeX files."""
    return process_latex_files(
        source_dir=source_dir,
        output_dir=output_dir,
        process_type='resume',
        model_name=model_name,
        max_files=max_files,
        api_delay=api_delay,
        force_reprocess=force_reprocess,
        debug=debug,
        analysis_only=analysis_only
    )

def extract_all(
    source_dir: str,
    output_dir: str,
    model_name: str = "gemini-2.0-flash",
    max_files: Optional[int] = None,
    api_delay: float = 5.0,
    force_reprocess: bool = False,
    debug: bool = False,
    analysis_only: bool = False
) -> Dict[str, Any]:
    """
    Process LaTeX files to extract both metadata and resumés.
    
    Args:
        source_dir: Directory containing LaTeX files
        output_dir: Directory to save results
        model_name: Gemini model to use
        max_files: Maximum number of files to process (None for all)
        api_delay: Delay between API calls in seconds
        force_reprocess: Whether to reprocess existing files
        debug: Whether to print debug information
        analysis_only: If True, skips API calls and just analyzes what would be done
        
    Returns:
        Dictionary with combined results
    """
    print("=== EXTRACTION DES MÉTADONNÉES ET RÉSUMÉS ===")
    return process_latex_files(
        source_dir=source_dir,
        output_dir=output_dir,
        process_type='both',
        model_name=model_name,
        max_files=max_files,
        api_delay=api_delay,
        force_reprocess=force_reprocess,
        debug=debug,
        analysis_only=analysis_only
    )
